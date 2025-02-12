import os

from airflow import DAG 

from config import config
from datetime import datetime,timedelta
from utils.requests_task import RequestGazettesTask
from utils.generate_index_task import GenerateIndexTask
# from utils.preprocess_documents import PreprocessDocuments
from utils.init_folders_task import InitFoldersTask
from utils.download_content_from_s3_bucket import DownloadContentFromS3
from utils.upload_contents_to_s3_bucket import UploadContentsToS3
from utils.preprocess_documents_simplified import PreprocessDocuments

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 1, 20),
    'end_date': datetime(2025, 10, 10),
    'schedule_interval': timedelta(days=1),
}


with DAG(
    'pull_gazettes_data',
    default_args=default_args,
    description='DAG created to pull data from Querido Diário and dump the text somewhere',
) as dag:
    
    init_folders_task = InitFoldersTask(
        task_id='init_folders_task',
        folders=[
            config.INGESTION_CHECKPOINT_LOGS_PATH,
            config.RAW_DOCUMENTS_DOWNLOAD_FOLDER,
            config.PREPROCESSED_FOLDER_PATH,
            config.PDF_SINGLE_PAGE_FOLDER,
            config.INDEX_DB_FOLDER,
        ]
    )

    request_task = RequestGazettesTask(
            task_id='request_gazettes_task',
            api_base_url=config.API_BASE_URL, 
            file_ingestion_metadata_path=config.RAW_DOCUMENT_API_REQUEST_LOG_PATH,
            max_size_per_request=config.MAX_SIZE_PER_REQUEST,
            territory_ids=config.TERRITORY_IDS,
            pull_start_date='{{ macros.ds_add(ds, -60)}}',
            pull_end_date='{{ macros.ds_add(ds, -1)}}',
            download_folder=config.RAW_DOCUMENTS_DOWNLOAD_FOLDER,
            default_args=default_args,
    )

    # Pre-process texts before generating indexing
    # preprocess_documents_task = PreprocessDocuments(
    #     task_id='preprocess_documents_task',
    #     preprocess_log_path=config.PREPROCESSED_DOCUMENTS_LOG_PATH,
    #     files_to_preprocess_path=config.RAW_DOCUMENTS_DOWNLOAD_FOLDER,
    #     single_page_folder=config.PDF_SINGLE_PAGE_FOLDER,
    #     preprocessed_files_folder=config.PREPROCESSED_FOLDER_PATH,
    #     default_args=default_args,
    #     max_pages_per_document=config.MAX_PAGES_PER_DOCUMENT,
    #     max_image_height=config.MAX_IMAGE_HEIGHT,
    #     max_image_width=config.MAX_IMAGE_WIDTH,
    # )

    preprocess_documents_task = PreprocessDocuments(
        task_id='preprocess_documents_task',
        preprocess_log_path=config.PREPROCESSED_DOCUMENTS_LOG_PATH,
        files_to_preprocess_path=config.RAW_DOCUMENTS_DOWNLOAD_FOLDER,
        preprocessed_files_folder=config.PREPROCESSED_FOLDER_PATH,
        default_args=default_args,
    )
    
    download_contents_version_from_s3_task = DownloadContentFromS3(
        task_id='download_contents_version_from_s3_task',
        bucket_name=config.S3_BUCKET_NAME,
        s3_conn_id=config.S3_CONN_ID,
        s3_key_to_local_filename={
            f'vector_db/{config.INDEX_DB_FILE}': os.path.join(config.INDEX_DB_FOLDER, 'index.faiss'),
            f'vector_db/{config.INDEX_DB_PICKLE}': os.path.join(config.INDEX_DB_FOLDER, 'index.pkl'),
            f'ingestion_checkpoint_logs/{config.INDEX_COLLECTION_FILE}': config.INDEX_COLLECTION_PATH,
            f'ingestion_checkpoint_logs/{config.RAW_DOCUMENT_API_REQUEST_LOG_FILE}': config.RAW_DOCUMENT_API_REQUEST_LOG_PATH,
            f'ingestion_checkpoint_logs/{config.PREPROCESSED_DOCUMENTS_LOG_FILE}': config.PREPROCESSED_DOCUMENTS_LOG_PATH
        }
    )

    generate_indexes_task = GenerateIndexTask(
        task_id='generate_indexes_task',
        db_path=config.INDEX_DB_FOLDER,
        collection_file_path=config.INDEX_COLLECTION_PATH,
        metadata_path=config.PREPROCESSED_DOCUMENTS_LOG_PATH,
        document_base_path=config.PREPROCESSED_FOLDER_PATH,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        embedding_size=config.EMBEDDING_SIZE,
        index_db_file=config.INDEX_DB_FILE,
    )

    upload_contents_to_s3_task = UploadContentsToS3(
        task_id='upload_contents_to_s3_task',
        bucket_name=config.S3_BUCKET_NAME,
        s3_conn_id=config.S3_CONN_ID,
        s3_path_to_local_filepath={
            'ingestion_checkpoint_logs/': config.INGESTION_CHECKPOINT_LOGS_PATH,
            'texts/': config.RAW_DOCUMENTS_DOWNLOAD_FOLDER,
            'preprocessed_documents': config.PREPROCESSED_FOLDER_PATH,
            'vector_db/': config.INDEX_DB_FOLDER,
        }
    )

    init_folders_task >> download_contents_version_from_s3_task >> request_task 
    request_task >> preprocess_documents_task >> generate_indexes_task >> upload_contents_to_s3_task