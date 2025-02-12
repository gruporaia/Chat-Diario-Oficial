import os 

API_BASE_URL = "https://queridodiario.ok.org.br/api/gazettes"
MAX_SIZE_PER_REQUEST = 100
RAW_DOCUMENTS_DOWNLOAD_FOLDER = '/usr/local/airflow/data/texts'
TERRITORY_IDS = '3106200'

INGESTION_CHECKPOINT_LOGS_PATH = '/usr/local/airflow/data/ingestion_checkpoint_logs'


RAW_DOCUMENT_API_REQUEST_LOG_FILE = 'log_urls.csv'
RAW_DOCUMENT_API_REQUEST_LOG_PATH = os.path.join(INGESTION_CHECKPOINT_LOGS_PATH, RAW_DOCUMENT_API_REQUEST_LOG_FILE)

INDEX_COLLECTION_FILE = 'collection.json'
INDEX_COLLECTION_PATH = os.path.join(INGESTION_CHECKPOINT_LOGS_PATH, INDEX_COLLECTION_FILE)

INDEX_DB_FOLDER = '/usr/local/airflow/data/vector_db/'
INDEX_DB_FILE = 'index.faiss'
INDEX_DB_PICKLE = 'index.pkl'

PREPROCESSED_DOCUMENTS_LOG_FILE = 'preprocessed_documents_log.csv'
PREPROCESSED_DOCUMENTS_LOG_PATH = os.path.join(INGESTION_CHECKPOINT_LOGS_PATH, PREPROCESSED_DOCUMENTS_LOG_FILE)

PDF_SINGLE_PAGE_FOLDER = '/usr/local/airflow/data/pdf_single_page/'
PREPROCESSED_FOLDER_PATH = '/usr/local/airflow/data/preprocessed_documents/'

MAX_PAGES_PER_DOCUMENT = 1
MAX_IMAGE_WIDTH = 600
MAX_IMAGE_HEIGHT = 600

S3_CONN_ID = 'minio_s3_conn_id'
S3_BUCKET_NAME = 'diario-oficial-db-dump'

CHUNK_SIZE = 2000
EMBEDDING_SIZE = 4096
CHUNK_OVERLAP = 500
