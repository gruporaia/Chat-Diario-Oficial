import os
import config
import json 
import logging 
import cohere

import boto3
from botocore.client import Config

from typing import Callable, Union
from fastapi import FastAPI
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from langchain_community.vectorstores import FAISS
from langchain_cohere import CohereEmbeddings

app = FastAPI()
app.index_db = None

logger = logging.getLogger('uvicorn.error')

class MessageRequestModel(BaseModel):
    message: str


def load_index_database():
    if not os.path.exists(config.LOCAL_INDEX_FILE_PATH) or not os.path.exists(config.LOCAL_INDEX_PICKLE_FILE_PATH):
        raise FileNotFoundError(f"FAISS files were not found")
    
    embeddings = CohereEmbeddings(
        model='embed-multilingual-v2.0', 
        base_url='https://stg.api.cohere.ai', 
        cohere_api_key=config.COHERE_API_KEY
    )
    
    vector_store = FAISS.load_local(
        config.LOCAL_INDEX_DB_BASE_PATH, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    
    return vector_store


def get_cohere_client():
    return cohere.Client(
        base_url='https://stg.api.cohere.ai', 
        api_key=config.COHERE_API_KEY
    )


# Function to fetch file from S3
def update_index_files_from_s3() -> bool:
    logger.info('Updating index')

    try: 
        client = boto3.client(
            's3',
            endpoint_url=config.AWS_HOST,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
    
        client.download_file(
            config.S3_BUCKET_NAME, 
            config.S3_INDEX_PATH, 
            config.LOCAL_INDEX_FILE_PATH
        )

        client.download_file(
            config.S3_BUCKET_NAME, 
            config.S3_INDEX_PICKLE_PATH, 
            config.LOCAL_INDEX_PICKLE_FILE_PATH
        )
    except Exception as e:
        logger.info(f'Error with index files: {e}. Failed to retrieve index from object storage')
        app.index_db = None
        return False
    
    app.index_db = load_index_database()
    logger.info(f'index db fetched: {app.index_db}')

    return True


@app.on_event("startup")
def on_startup():
    """
    Run the scheduler to fetch the S3 file periodically.
    """
    update_index_files_from_s3()  # Initial fetch
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_index_files_from_s3, "interval", hours=24)
    scheduler.start()
    logger.info("Started scheduler to update index.")


def rag_context_similarity_search(query: str, k=int):
    if app.index_db is None:
        logger.info(f'Index failed to fetch, trying again')
        if not update_index_files_from_s3():
            raise Exception('Backend failed to get index')

    logger.info(f"Similarity search on: {app.index_db}")

    result = app.index_db.similarity_search(query, k=k)
    return ''. join([doc.page_content for doc in result])

def no_enrich_fn(cohere_api_client, question: str, temperature: float = 0.7):
    return question


def enrich_query(cohere_api_client, question: str, temperature: float = 0.7):
    prompt = f"""
    Você receberá uma pergunta e deverá identificar os termos mais importantes, destacá-los e replicá-los ao final da pergunta.
    Os termos mais importantes geralmente consituem números de acórdãos, números de processos, nomes de órgãos públicos brasileiros e nomes de pessoas.
    Exemplo:
    Pergunta: "Qual é o impacto do Acórdão nº 11.086/2ª na jurisprudência?"
    Saída: "Qual é o impacto do Acórdão nº 11.086/2ª na jurisprudência? Acórdão nº 11.086/2ª Acórdão nº 11.086/2ª jurisprudência jurisprudência."

    Pergunta: "{question}"
    """
    logger.info(question)

    response = cohere_api_client.chat_stream(
        message=prompt,
        model="command-r-plus-08-2024",
        temperature=temperature,
        preamble=""
    )

    new_query = ''.join([
        event.text
        for event in response 
        if event.event_type == "text-generation"
    ])

    logger.info(f"New question: {new_query}")
    
    return new_query


def answer_question_expanded_search(cohere_api_client, question, temperature: float = 0.7, k: int = 3):
    current_k = k
    while current_k <= config.MAX_K:
        answer, context = answer_question_chat_stream_with_context(cohere_api_client, question=question, temperature=0.7, k=current_k)
        logger.info(f"\nAnswer with k={current_k}: {answer}")

        if answer == "" or answer == " " or answer == "\n":
            logger.info(f"\nAnswer with k={current_k} not satisfactory. Trying again with k ={current_k + 3}...\n")
            current_k += 3
            continue

        message = f"""
                    Você receberá uma resposta gerada. Considerando o contexto a seguir, classifique-a, considerando que uma resposta ruim não apresenta conteúdo.
                    Usualmente, essa reposta contém os termos "Desculpe", "Não fui capaz", "Não foi possível", "Não encontrei".
                    Caso a resposta esteja ruim conforme os critérios anteriomente explicados, responda apenas "RUIM", caso contrário, responda "BOA".
                    Contexto: {context}
                    Resposta: {answer}
        """
        
        response = cohere_api_client.chat_stream(
            message=message,
            model="command-r-plus-08-2024",
            temperature=temperature,
            preamble=""
        )

        new_query = ''.join([
            event.text
            for event in response 
            if event.event_type == "text-generation"
        ])

        if(new_query == "RUIM"):
            logger.info(f"\nAnswer with k={current_k} not satisfactory. Trying again with k ={current_k + 3}...\n")
            current_k += 3
        else:
            logger.info(f"\nAnswer with k={current_k} was good.\n") 
            break

    return answer, context


def answer_question_chat_stream_with_context(
        cohere_api_client,
        question: str, 
        temperature: float = 0.7, 
        k: int = 3, 
    ):

    context = rag_context_similarity_search(question, k)
    logger.info(f'Context: {context}')

    prompt = f"""Considere os seguintes trechos de documentos como contexto: {context}
    Com base em tudo o que foi citado, responda a seguinte questão: {question}"""
    logger.info(f'Prompt: {prompt}')
    
    response = cohere_api_client.chat_stream(
        message=prompt,
        model="command-r-plus-08-2024",
        temperature=temperature,
        preamble=""
    )
    logger.info(f'Response: {response}')

    output = ''.join([
        event.text
        for event in response 
        if event.event_type == "text-generation"
    ])

    logger.info(f"Answer: {output}")
    
    return output, context


def answer_question(
        cohere_api_client,
        question: str, 
        query_enricher_fn: Callable,
        query_answer_fn: Callable, 
        temperature: float = 0.7,
        k: int = 3):
    
    enriched_query = query_enricher_fn(cohere_api_client, question, temperature)
    answer = query_answer_fn(cohere_api_client, enriched_query, temperature, k)
    return answer


@app.post("/chat")
def chat_endpoint(user_input: MessageRequestModel):
    """
    Process chat input and respond using the index data.
    """

    if app.index_db is None:
        update_index_files_from_s3()

    cohere_api_client = get_cohere_client()

    answer, _ = answer_question(
        cohere_api_client,
        user_input.message,
        query_enricher_fn=no_enrich_fn,
        query_answer_fn=answer_question_expanded_search,
        temperature=config.TEMPERATURE,
        k=config.K_SIMILARITY_SEARCH,
    )

    return {
        "processed_input": {user_input.message},
        "answer": {answer},
    }