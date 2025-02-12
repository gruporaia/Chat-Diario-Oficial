import os
import json
import faiss
import time 
import random 

from langchain_cohere import CohereEmbeddings
from langchain_core.embeddings.embeddings import Embeddings 

from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.schema.document import Document

from typing import List, Any, Dict
from dataclasses import dataclass, field

from airflow.models.baseoperator import BaseOperator
from airflow.models import Variable

from pydantic import BaseModel

import pandas as pd

class FileMetadata(BaseModel):
    uuid: str

class ChunksMetadata(BaseModel):
    chunks: List[str] 
    chunk_size: int
    embedding_size: int
    chunk_overlap: int

class Doc(BaseModel):
    chunks_metadata: ChunksMetadata
    file_metadata: FileMetadata

class DocumentCollection(BaseModel):
    documents: Dict[str, Doc]


class GenerateIndexTask(BaseOperator):
    embeddings: Embeddings = field(init=False)
    vector_store: FAISS = field(init=False)
    index: faiss.IndexFlatIP = field(init=False)
    collection: DocumentCollection = field(init=False)
    
    def __init__(
            self, 
            task_id: str,
            db_path: str, 
            collection_file_path: str,
            metadata_path: str,
            document_base_path: str,
            index_db_file: str,
            chunk_size: str=1000,
            chunk_overlap: int=200,
            embedding_size: int=4096,
            **kwargs
        ) -> None:

        super(GenerateIndexTask, self).__init__(task_id=task_id, **kwargs)
        
        self.db_path = db_path
        self.collection_file_path = collection_file_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_size = embedding_size
        self.metadata_path = metadata_path
        self.document_base_path = document_base_path
        self.index_db_file = index_db_file


    def init_file_metadata(self):
        metadata = pd.read_csv(self.metadata_path)
        
        file_metadata_list = [
            FileMetadata(uuid = file["file_uuid_breakdown"])
            for _, file in metadata.iterrows()
            if file['file_uuid_breakdown'] not in self.collection.documents
        ]

        print(file_metadata_list)
        
        return file_metadata_list


    def init_db(self):
        self.embeddings = CohereEmbeddings(
            model='embed-multilingual-v2.0',
            base_url='https://stg.api.cohere.ai',
            cohere_api_key=Variable.get('cohere_api_key')
        )
        self.embedding_size = len(self.embeddings.embed_query("hello world"))
        self.index = faiss.IndexFlatIP(self.embedding_size)


    def parse_db_current_state(self):
        if os.path.exists(os.path.join(self.db_path, self.index_db_file)):
            print(f"loading database {self.db_path}")
            
            self.vector_store = FAISS.load_local(
                self.db_path, self.embeddings, allow_dangerous_deserialization=True
            )

            with open(os.path.join(self.db_path, self.collection_file_path), "r") as f:
                content = f.read()
                content = json.loads(content)
                self.collection = DocumentCollection(**content)
        else:
            print(f"instantiating new database {self.db_path}")

            self.vector_store = FAISS(
                embedding_function=self.embeddings,
                index=self.index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
            
            self.collection = DocumentCollection(documents={})

    
    def update_collection(self, vector_db_ids, file_metadata: FileMetadata):
        self.collection.documents[file_metadata.uuid] = Doc(
            chunks_metadata=ChunksMetadata(
                chunks=vector_db_ids,
                embedding_size=self.embedding_size,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            ),
            file_metadata=file_metadata
        )


    def add_document(self, path: str, file_metadata: FileMetadata):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 

        with open(path, 'r') as f:
            document_content = f.read()
        
        docs = [
            Document(page_content=x, metadata=file_metadata.model_dump()) 
            for x in text_splitter.split_text(document_content)
        ]
        chunks_uuids = [f"{file_metadata.uuid}_chunk{i}" for i in range(len(docs))]
        vector_db_ids = self.vector_store.add_documents(documents=docs, ids=chunks_uuids)
        
        self.update_collection(vector_db_ids, file_metadata)
        print(f"Added {len(vector_db_ids)} chunks for document: {file_metadata.uuid}")

        print('Saving current vector index status')
        self.save_index_current_state()

        # Making sure we do not create multiple requests per second to cohere API
        sleep_interval = random.randint(1, 10)

        print(f'Waiting {sleep_interval} seconds')
        time.sleep(sleep_interval) 

        return vector_db_ids


    def add_batch_documents(self, file_metadata_list: List[FileMetadata]):
        document_uuid_to_extension_map = {}
        for file in os.listdir(self.document_base_path):
            print(file)
            uuid, extension = file.split('.')
            document_uuid_to_extension_map[uuid] = extension 

        for file_metadata in file_metadata_list:
            print(file_metadata)
            if file_metadata.uuid in document_uuid_to_extension_map:
                print(file_metadata.uuid)
                file_name = f"{file_metadata.uuid}.{document_uuid_to_extension_map[file_metadata.uuid]}"
                path = os.path.join(self.document_base_path, file_name)
                print(path)
                self.add_document(path, file_metadata)
            

    def save_index_current_state(self):
        self.vector_store.save_local(self.db_path)
        
        with open(os.path.join(self.db_path, self.collection_file_path), "w") as f:
            output = self.collection.model_dump_json(indent=4)
            f.write(output)


    def init_folders(self):
        if not os.path.exists(self.db_path):
            print(f'DB folder: {self.db_path} does not exists, creating it.')
            os.makedirs(self.db_path)
    
        if not os.path.exists(os.path.dirname(self.metadata_path)):
            print(f'DB folder: {os.path.dirname(self.metadata_path)} does not exists, creating it.')
            os.makedirs(os.path.dirname(self.metadata_path))


    def execute(self, context):
        self.init_folders()

        print('Initializing database')
        self.init_db()

        print('Parsing database current state')
        self.parse_db_current_state()

        print('Reading file metadata')
        file_metadata_list = self.init_file_metadata()
        print(file_metadata_list)

        print('Adding batch of documents')
        self.add_batch_documents(file_metadata_list)
        