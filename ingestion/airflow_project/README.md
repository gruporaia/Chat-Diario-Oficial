# Ingestão de dados
## Funcionamento
1. O pipeline executa requests para a API do Querido Diário, fazendo download de arquivos PDFs de documentos publicados pelo Diário Oficial. 

2. Os PDFs são pré-processados por meio da biblioteca docling, gerando arquivos `.md` com o texto. Como os PDFs podem ser arbitrariamente grandes, é feito a quebra por página (de acordo com a configuração `MAX_PAGES_PER_DOCUMENT`).

3. A partir destes documentos, é construído um índice vetorial por meio da biblioteca FAISS, com base em embeddings gerados pela Cohere.

4. Os PDFs e o índice final gerado são enviados para um bucket no S3/Minio, permitindo que seja compartilhado entre diferentes serviços.
   
<p align="center">
    <img width="900" src="https://github.com/user-attachments/assets/6456d175-4758-41c0-90e3-4d7667c7c02a" alt="Ingestão de dados - Diagrama">
</p>

## Configuração do Docker + Airflow
Projeto de ingestão de dados utiliza do Airflow. Para isso, utilizamos Docker para tornar mais prático o desenvolvimento.
Para isso, siga as seguintes instruções: 
* Criar os volumes `./logs` e `./plugins`: `mkdir ./logs ./plugins`. Aqui serão salvos diversos metadados do Airflow.
* O volume `./dags` é requisitado, mas já está no diretório necessário. Neste diretório estão os DAGs, que correspondem ao pipeline e as tarefas customizadas que realizam os passos do projeto, sendo orquestradas pelo Airflow.
* Rodar o comando `docker-compose up airflow-init`: isso vai fazer com que o Airflow inicialize o projeto.
* Rodar o comando `docker-compose up`: isso vai subir todos os containers necessários, como o scheduler, worker e o webserver, no qual é apresentada uma UI para que possamos admnistrar o Airflow.

## Minio / S3
O Minio é um Object Storage de desenvolvimento local, que possui uma interface idêntica a AWS S3. Corresponde a um serviço criado junto ao docker-compose do Airflow, e que pode ser acessado localmente. Nele são armazenados os dados dentro de Buckets. 

Dentro do Minio, é necessário criar uma chave de acesso, que será utilizada para permitir a conexão entre o airflow e a object storage. Para isso, basta ir em Access Keys > Create access Key e copiar os valores de Access Key e Secret Key.

Agora, devemos adicionar uma conexão dentro do Airflow. Para isso, basta ir na interface visual do Airflow > conexões > adicionar conexão > selecionar Amazon Web Services > adicionar o seguinte JSON ao campo "extra": 
```
{
  "aws_access_key_id": "<SUA CHAVE AWS>",
  "aws_secret_access_key": "<SEU SEGREDO AWS>",
  "host": "http://host.docker.internal:9000"
}
```

## Cohere
Utilizamos a API da cohere para realizar o Embedding dos textos. A chave no Airflow é obtida por meio do conceito de Airflow Variables. Para isso, basta ir em Admin > botão '+' para adicionar > `Key = "cohere_api_key"` > `Val = "\<sua chave da cohere\>"`.

Mais informações podem ser encontradas em: https://airflow.apache.org/docs/apache-airflow/2.1.1/start/docker.html.
