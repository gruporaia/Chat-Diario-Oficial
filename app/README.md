# **Aplicação**

## **Funcionamento**
O App desenvolvido neste respositório corresponde a um backend (em `./app`) e um frontend (em `./frontend`). O backend está conectado à object storage Minio/S3 que é construída e mantida pelo pipeline de ingestão e orquestrado pelo Airflow. A principal funcionalidade é permitir com que um usuário forneça uma questão de input, que é então enviado consumido pelo backend e utilizado para fazer query no FAISS Vector database. Os N documentos extraidos pele indexação são utilizados para enriquecer o prompt que é enviado para um gerador de texto.

<p align="center">
    <img width="800" src="https://github.com/user-attachments/assets/4c56fd4a-218d-4b7d-9148-f6a0ff44d1af" alt="Aplicação - Diagrama">
</p>

## **Rodar a aplicação**
Para rodar a aplicação, é necessário ter uma versão do Minio instanciada ou um AWS S3 para que seja possível conectar à object storage e puxar os arquivos necessários para formar o índice FAISS. 

O comando `docker-compose up` irá criar um servidor local do Minio. Dentro do object storage, é preciso adicionar um bucket com o nome `diario-oficial-db-dump` com arquivos `index.faiss` e `index.pkl` dentro de um pasta denominada `vector_db`. Isso está indicado em `./app/config.py`, que configura as principais constantes para a aplicação e que pode ser atualizado de acordo com o seu ambiente de desenvolvimento/produção. 

Em `./app/config.py` temos:
```py
# Chaves de acesso ao object storage
AWS_ACCESS_KEY_ID='*********' 
AWS_SECRET_ACCESS_KEY='****************************'
AWS_HOST='http://host.docker.internal:9000'

# Identificador dos buckets e objetos dentro do object storage 
S3_BUCKET_NAME='diario-oficial-db-dump'
S3_INDEX_PATH='vector_db/index.faiss'
S3_INDEX_PICKLE_PATH='vector_db/index.pkl'

# Identificadores dos objetos criados localmente e consumidos pelo backend
LOCAL_INDEX_DB_BASE_PATH='vector_db'
LOCAL_INDEX_FILE_PATH=LOCAL_INDEX_DB_BASE_PATH + '/index.faiss'
LOCAL_INDEX_PICKLE_FILE_PATH=LOCAL_INDEX_DB_BASE_PATH + '/index.pkl'

# Configuração para utilização da API da Cohere e 
# parâmetros para o modelo de geração de texto
COHERE_API_KEY='****************************'
TEMPERATURE=0.7
K_SIMILARITY_SEARCH=3
```

Para rodar a aplicação, basta rodar o comando `docker-compose up`, subindo tanto o frontend quanto o backend.

