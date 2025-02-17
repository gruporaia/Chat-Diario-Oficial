# Chat Diário Oficial

O **Chat Diário Oficial** é uma solução end-to-end desenvolvida para otimizar a busca de informações em longas bases de dados textuais, como o Diário Oficial do Município de Belo Horizonte (MG). Utilizando conceitos de Retrieval Augmented Generation (RAG), este projeto visa auxiliar servidores públicos e profissionais que precisam navegar diariamente por extensos documentos, proporcionando uma experiência de busca eficiente e economia de tempo.

[Demo](https://github.com/user-attachments/assets/ebe3fcad-f528-42c2-949e-d627202bad7e)

## Design & Arquitetura 
![Design sem nome](https://github.com/user-attachments/assets/26a7d6b0-76c5-4ad6-9bf4-c4b4f204ae81)
## Ingestão de Dados

A etapa de ingestão de dados tem como objetivo principal coletar, processar e armazenar os Diários Oficiais Municipais de forma estruturada, disponibilizando os dados para consulta pela aplicação principal.

### **Pipeline de Ingestão**

1.  **Coleta dos Documentos**
    
    -   Os Diários Oficiais são extraídos da API do [Querido Diário](https://ok.org.br/projetos/querido-diario/), um projeto que centraliza dados obtidos via _scraping_ de diversas cidades, como Belo Horizonte.
2.  **Pré-processamento dos Arquivos**
    
    -   Os documentos, inicialmente no formato `PDF`, são convertidos para `TXT`, limpados e pré-processados.
3.  **Fragmentação do Texto**
    
    -   O texto extraído é segmentado em _chunks_ (trechos menores) de até 2000 caracteres, otimizando a busca e o armazenamento vetorial.
4.  **Geração de Embeddings e Armazenamento**
    
    -   Para cada _chunk_, é gerado um _embedding_, que representa semanticamente o conteúdo do trecho.
    -   Esses _embeddings_ são armazenados em um banco de dados vetorial junto com seus metadados, como:
        -   Identificador único;
        -   Data do diário;
        -   Tamanho do _embedding_;
        -   Outras informações relevantes.
5.  **Persistência no Object Storage**
    
    -   O banco de dados vetorial atualizado, juntamente com os arquivos processados, é armazenado em um _bucket_ de _Object Storage_, garantindo sua disponibilidade para consumo pela aplicação.

----------

### **Tecnologias Utilizadas**

-   **[Apache Airflow](https://airflow.apache.org/):**  Responsável pela orquestração e _scheduling_ da pipeline, garantindo a execução diária e a importação contínua dos documentos recém-publicados.
    
-   **[Faiss](https://ai.meta.com/tools/faiss/):**  Banco de dados vetorial otimizado para armazenar e recuperar _embeddings_ de forma eficiente.
    
-   **[LangChain](https://www.langchain.com/):**  Biblioteca que facilita a integração com _LLMs_ e ferramentas de processamento de texto.
    -   Utilizamos o modelo `embed-multilingual-v2.0` da [Cohere](https://cohere.com/) para geração dos _embeddings_.
-   **[MinIO](https://min.io/):** _Object Storage_ de código aberto utilizado para armazenamento local durante a fase de desenvolvimento.
    
    -   Possui a mesma interface do AWS S3, facilitando a transição entre os ambientes de desenvolvimento e produção através de variáveis de ambiente.
# Question Answering

Esta etapa é responsável pelo processamento da pergunta do usuário, busca por similaridade na base vetorial para a construção do contexto e geração da resposta para a pergunta.

## 1. Tecnologias

A arquitetura é baseada na técnica **Retrieval-Augmented Generation (RAG)**, reunindo trechos relevantes dos documentos e utilizando-os como contexto para as perguntas. Os trechos são obtidos através de uma busca por similaridade em base de dados vetorial (FAISS), e as respostas obtidas através da API da Cohere.

### 1.1. MinIO
- **Aplicação:** Utilizado para o armazenamento dos arquivos referentes à base vetorial. Após o *download*, os mesmos são carregados em memória.
- **Documentação:** [MinIO Documentation](https://docs.min.io/)

### 1.2. FAISS
- **Aplicação:** Utilizado para realizar a busca por similaridade nos documentos disponíveis, com o objetivo de construir o contexto necessário para a resposta da pergunta realizada pelo usuário.
- **Index.faiss?** Armazena os vetores dos documentos presentes na base para que sejam utilizados na busca por similaridade.
- **Index.plk?** Arquivo binário que armazena dados serializados posteriormente utilizados para a recuperação de informação no processo de busca.
- **Documentação:** [FAISS Documentation](https://github.com/facebookresearch/faiss)

### 1.3. LangChain
- **Aplicação:** Utilizada como facilitadora da integração entre a base vetorial e o processo de geração de respostas.
- **Documentação:** [LangChain Documentation](https://www.langchain.com/)

### 1.4. Cohere API
- **Aplicação:** Utilizada para a implementação do processo de geração de respostas.
- **Cohere Chat-Stream:** Método usado para a interação do modelo em tempo real, gerando respostas através de *request* realizada à API.
- **Modelo command-r-plus-08-2024:** Modelo pré-treinado e multilingual adequado para tarefas de *question answering*.
- **Documentação:** [Cohere Documentation](https://cohere.ai/docs)

## 2. Pipeline

1. **Download da base de dados:** A base de dados vetorial é baixada do MinIO.
2. **Entrada do Usuário:** O usuário fornece uma pergunta através da interface visual da aplicação.
3. **Enriquecimento da Pergunta:** Através da função *enrich_query*, a pergunta do usuário é multiplicada através da replicação de termos "chave". Isso atribui mais peso a termos de maior importância, tais como números de artigos ou nomes de órgãos públicos mencionados, possibilitando uma busca mais precisa.
4. **Recuperação de Dados (FAISS):** Através de uma busca por similaridade, o sistema recupera os documentos mais relevantes para responder a pergunta do usuário.
5. **Geração de Resposta (Cohere):** Uma requisição à API da Cohere é realizada para que uma resposta seja gerada.
6. **Validação da resposta:** O mesmo modelo é utilizado para a validação da resposta gerada, conferindo se a mesma está de acordo com o contexto fornecido. Em caso negativo, a busca por similaridade é refeita, dessa vez retornando mais documentos, e uma nova resposta é gerada, agora com um maior contexto.

## Funcionamento
- [Funcionamento do pipeline de extração dos dados](https://github.com/gruporaia/Chat-Diario-Oficial/tree/main/ingestion/airflow_project)
- [Funcionamento da aplicação](https://github.com/gruporaia/Chat-Diario-Oficial/tree/main/app)

TODO: exemplos de interação

## Quem somos

Este projeto foi desenvolvido pelos membros do **RAIA (Rede de Avanço de Inteligência Artificial)**, uma iniciativa estudantil do Instituto de Ciências Matemáticas e de Computação (ICMC) da USP - São Carlos. O RAIA é um grupo formado por estudantes que compartilham o objetivo de criar soluções inovadoras utilizando inteligência artificial para impactar positivamente a sociedade. Para saber mais, acesse <insta> ou <site>!
