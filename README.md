# Chat Diário Oficial

O **Chat Diário Oficial** é uma solução end-to-end desenvolvida para otimizar a busca de informações em longas bases de dados textuais, como o Diário Oficial do Município de Belo Horizonte (MG). Utilizando conceitos de Retrieval Augmented Generation (RAG), este projeto visa auxiliar servidores públicos e profissionais que precisam navegar diariamente por extensos documentos, proporcionando uma experiência de busca eficiente e economia de tempo.

## Design & Arquitetura 

![Group 38](https://github.com/user-attachments/assets/0747e95b-ec41-4cb9-86b1-d2e2035bdb1e)

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

## Question Answering

A etapa de *Question Answering* tem como objetivo processar a pergunta do usuário, recuperar trechos relevantes da base vetorial e gerar uma resposta fundamentada no contexto identificado.

### **Pipeline de Question Answering**

1. **Download da Base de Dados**
    - A base de dados vetorial é baixada do *Object Storage* MinIO e carregada em memória para consulta eficiente.
    
2. **Entrada do Usuário**
    - O usuário submete uma pergunta através da interface da aplicação.
    
3. **Enriquecimento da Pergunta**
    - A função *enrich_query* expande a consulta, atribuindo maior peso a termos-chave, como números de artigos e nomes de órgãos públicos, aumentando a precisão da busca.
    
4. **Recuperação de Dados**
    - A busca por similaridade é realizada no banco vetorial *FAISS*, retornando os documentos mais relevantes para compor o contexto da resposta.
    
5. **Geração de Resposta**
    - O modelo *command-r-plus-08-2024*, da API Cohere, gera uma resposta com base nos trechos recuperados.
    
6. **Validação da Resposta**
    - O mesmo modelo verifica a adequação da resposta ao contexto. Caso necessário, mais documentos são recuperados e uma nova resposta é gerada com um contexto expandido.

## **Tecnologias Utilizadas**

-   **[Apache Airflow](https://airflow.apache.org/):**  Responsável pela orquestração e _scheduling_ da pipeline, garantindo a execução diária e a importação contínua dos documentos recém-publicados.

-   **[MinIO](https://min.io/):** _Object Storage_ de código aberto utilizado para armazenamento local durante a fase de desenvolvimento.
    
    -   Possui a mesma interface do AWS S3, facilitando a transição entre os ambientes de desenvolvimento e produção através de variáveis de ambiente.

-   **[Faiss](https://ai.meta.com/tools/faiss/):**  Banco de dados vetorial otimizado para armazenar e recuperar _embeddings_ de forma eficiente. Utilizado para realizar a busca por similaridade nos documentos disponíveis, com o objetivo de construir o contexto necessário para a resposta da pergunta realizada pelo usuário.
    - **Index.faiss:** Armazena os vetores dos documentos presentes na base para que sejam utilizados na busca por similaridade.
    - **Index.pkl:** Armazena dados serializados para recuperação posterior.

-   **[LangChain](https://www.langchain.com/):**  Biblioteca que facilita a integração com _LLMs_ e ferramentas de processamento de texto.
    -   Utilizamos o modelo `embed-multilingual-v2.0` da [Cohere](https://cohere.com/) para geração dos _embeddings_.

-   **[Cohere API](https://cohere.ai/docs):** Utilizada para a implementação do processo de geração de respostas.
    - **Cohere Chat-Stream:** Método usado para a interação do modelo em tempo real, gerando respostas através de *request* realizada à API.
    - **Modelo command-r-plus-08-2024:** Modelo pré-treinado e multilingual adequado para tarefas de *question answering*.


## Funcionamento
O Chat Diário Oficial pode ser testado localmente seguindo as instruções contidas nas páginas destacadas abaixo. Basta seguir o tutorial fornecido para configurar o ambiente e executar a aplicação, garantindo que todas as dependências estejam corretamente instaladas. A aplicação foi desenvolvida como uma prova de conceito e ainda requer melhorias para aprimorar sua eficiência e usabilidade. Interessados em contribuir para o seu desenvolvimento são bem-vindos e podem entrar em contato com o RAIA para colaborar. O teste desta ferramenta foi realizado com funcionários da Prefeitura de Belo Horizonte, permitindo validar seu funcionamento em um ambiente real.
- [Funcionamento do pipeline de extração dos dados](https://github.com/gruporaia/Chat-Diario-Oficial/tree/main/ingestion/airflow_project)
- [Funcionamento da aplicação](https://github.com/gruporaia/Chat-Diario-Oficial/tree/main/app)

## Quem somos
| ![LogoRAIA](https://github.com/user-attachments/assets/ce3f8386-a900-43ff-af84-adce9c17abd2) |  Este projeto foi desenvolvido pelos membros do **RAIA (Rede de Avanço de Inteligência Artificial)**, uma iniciativa estudantil do Instituto de Ciências Matemáticas e de Computação (ICMC) da USP - São Carlos. Somos estudantes que compartilham o objetivo de criar soluções inovadoras utilizando inteligência artificial para impactar positivamente a sociedade. Para saber mais, acesse [nosso site](https://gruporaia.vercel.app/) ou [nosso Instagram](instagram.com/grupo.raia)! |
|------------------|-------------------------------------------|
 
### **Desenvolvedores**
- **Alvaro Jose Lopes** - [LinkedIn](https://www.linkedin.com/in/alvaro-jose-lopes/) | [GitHub](https://github.com/AlvaroJoseLopes)
- **Bernardo Marques Costa** - [LinkedIn](https://www.linkedin.com/in/bernardo-marques-costa/) | [GitHub](https://github.com/bmarquescost)
- **Cecília Nunes Sedenho** - [LinkedIn](https://www.linkedin.com/in/cec%C3%ADlia-nunes-sedenho-305059255/) | [GitHub](https://github.com/HeNunes)
- **Laura Fernandes Camargos** - [LinkedIn](https://www.linkedin.com/in/laura-fernandes-camargos-a26b89246/) | [GitHub](https://github.com/laurafcamargos)
- **Pedro Augusto Monteiro Delgado** - [LinkedIn](https://www.linkedin.com/in/pedroamdelgado) | [GitHub](https://github.com/DelgadoPedro)


