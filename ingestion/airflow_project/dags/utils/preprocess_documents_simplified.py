import os
import pymupdf
import pandas as pd 

# from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
from typing import Dict, List, Set
from airflow.models.baseoperator import BaseOperator

class PreprocessDocuments(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            preprocess_log_path: str, 
            files_to_preprocess_path: str,
            preprocessed_files_folder: str,
            **kwargs
        ) -> None:

        super(PreprocessDocuments, self).__init__(task_id=task_id, **kwargs)
        
        self.files_to_preprocess_path = files_to_preprocess_path
        self.preprocess_log_path = preprocess_log_path
        self.preprocessed_files_folder = preprocessed_files_folder
        self.metadata: pd.DataFrame = None

    def get_already_preprocessed_metadata_from_csv(self):
        print('Checking pre processed documents log')
        print(self.preprocess_log_path, not os.path.isfile(self.preprocess_log_path))
        if not os.path.isfile(self.preprocess_log_path):
            return  pd.DataFrame(columns=['file_uuid', 'file_uuid_breakdown', 'etl_timestamp']) # return empty df 
        
        return pd.read_csv(self.preprocess_log_path)


    def get_already_preprocessed_documents_from_log(self, is_breakdown: bool = False):
        key = 'file_uuid' if not is_breakdown else 'file_uuid_breakdown'
        return set(self.metadata[key].to_list())


    def is_file_already_processed(self, source: str, is_breakdown: bool = False):
        return source in self.get_already_preprocessed_documents_from_log(is_breakdown)


    def save_preprocessed_documents(self, document, file_uuid, extension: str = '.txt'):
        print(f'Saving in path:', os.path.join(self.preprocessed_files_folder, file_uuid) + extension)
        with open(os.path.join(self.preprocessed_files_folder, file_uuid) + extension, 'w') as f:
            f.write(document)


    def preprocess_file(self, source: str):
        text = ""
        with pymupdf.open(os.path.join(self.files_to_preprocess_path, source)) as pdf_document:
            for page_number in range(len(pdf_document)):
                page = pdf_document[page_number]
                text += page.get_text()  # Extract text from the page
        text = text.replace('\n', ' ').replace('  ', ' ')
        return text


    def append_to_already_preprocessed_documents_log(self, file_uuid: str, file_uuid_breakdown: str, etl_timestamp: datetime):
        data_to_append = [{'file_uuid': file_uuid, 'file_uuid_breakdown': file_uuid_breakdown, 'etl_timestamp': etl_timestamp}] 
        if self.metadata is None or self.metadata.empty:
            self.metadata = pd.DataFrame(data_to_append)
        else: 
            self.metadata = pd.concat([self.metadata, pd.DataFrame(data_to_append)])
            self.metadata.to_csv(self.preprocess_log_path, index=False)
        
        return self.metadata 


    def process_files(self):
        for file in os.listdir(self.files_to_preprocess_path):
            file_uuid = file.split('.')[0]
    
            preprocessed_document = self.preprocess_file(file)

            if self.is_file_already_processed(file, is_breakdown=False):
                print(f'File {file} already preprocessed')
                continue 

            self.append_to_already_preprocessed_documents_log(
                file_uuid=file_uuid, 
                file_uuid_breakdown=file_uuid,
                etl_timestamp=datetime.now(), 
            )

            self.save_preprocessed_documents(preprocessed_document, file_uuid)


    def execute(self, context):
        self.metadata = self.get_already_preprocessed_metadata_from_csv()
        self.process_files()
        self.metadata.to_csv(self.preprocess_log_path, index=False)