import os
import pandas as pd 

import io
import pymupdf
from PIL import Image

# from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
from typing import Dict, List, Set
from airflow.models.baseoperator import BaseOperator
from docling.document_converter import DocumentConverter

class PreprocessDocuments(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            preprocess_log_path: str, 
            files_to_preprocess_path: str,
            single_page_folder: str,
            preprocessed_files_folder: str,
            max_pages_per_document: int = 10,
            max_image_width: int = 1000,
            max_image_height: int = 1000,
            drop_pages_with_images: bool = True,
            delete_after_processing: bool = True,
            **kwargs
        ) -> None:

        super(PreprocessDocuments, self).__init__(task_id=task_id, **kwargs)
        
        self.files_to_preprocess_path = files_to_preprocess_path
        self.preprocess_log_path = preprocess_log_path
        self.preprocessed_files_folder = preprocessed_files_folder
        self.single_page_folder = single_page_folder
        self.max_pages_per_document = max_pages_per_document
        self.max_image_width = max_image_width
        self.max_image_height = max_image_height
        self.delete_after_processing = delete_after_processing
        self.drop_pages_with_image = drop_pages_with_images

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


    def get_aggregated_pages(self, input_pdf):
        n_pages = list(range(len(input_pdf)))
        
        return [
            n_pages[i: i + self.max_pages_per_document] 
            for i in range(0, len(n_pages), self.max_pages_per_document)
        ]


    def remove_image_inside_page(self, input_page):
        images = input_page.get_images(full=True)
        
        for img in images:
            try:
                input_page.delete_image(img[0])
            except Exception as e:
                print(f'Returned exception: {e}')


    def has_big_image(self, input_page):
        images = input_page.get_images(full=True)
        for img in images:
            width, height = img[2], img[3]
            if width > self.max_image_width or height > self.max_image_height:
                return True 
        return False


    def breakdown_long_documents(self, source: str) -> List:
        # Break down documents by pages to avoid running out of memory
        print(f'Breaking down pdf {source} into multiple PDF single pages')
        already_breakdown_files = set(os.listdir(self.single_page_folder))

        source_path = os.path.join(self.files_to_preprocess_path, source)
        input_pdf = pymupdf.open(source_path)
        
        pages_split_ids = self.get_aggregated_pages(input_pdf)

        breakdown_files_path = []
        for subset in pages_split_ids:
            breakdown_filename_uuid = f"{source.split('.')[0]}-page-{min(subset)}-{max(subset)}"
            output_filename = f"{breakdown_filename_uuid}.pdf"
            output_path = os.path.join(self.single_page_folder, output_filename)
            
            if self.is_file_already_processed(breakdown_filename_uuid, is_breakdown=True):
                print(f'File {breakdown_filename_uuid} already preprocessed')
                continue 

            if output_filename in already_breakdown_files:
                print(f'File {output_filename} already broken down into')
            else:
                subset_filtered = [
                    page_id 
                    for page_id in subset 
                    if not self.has_big_image(input_pdf[page_id])
                ] if self.drop_pages_with_image else subset

                if len(subset_filtered) == 0:
                    continue 

                output = pymupdf.open()
                for page_id in subset_filtered:
                    output.insert_pdf(input_pdf, from_page=page_id, to_page=page_id)

                try:         
                    output.save(output_path)
                except ValueError:
                    print(f'Skipped file: {output_filename}')
                    continue
                finally:
                    output.close()
                            
            breakdown_files_path.append((output_filename, output_path))
        
        return breakdown_files_path


    def save_preprocessed_documents(self, document, file_uuid):
        print(f'Saving in path:', os.path.join(self.preprocessed_files_folder, file_uuid) + '.md')
        with open(os.path.join(self.preprocessed_files_folder, file_uuid) + '.md', 'w') as f:
            f.write(document)


    def preprocess_file(self, source: str):
        converter = DocumentConverter()
        result = converter.convert(source)
        return result.document.export_to_markdown() 


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
            single_page_files = self.breakdown_long_documents(file)
            for breakdown_filename, filepath in single_page_files:
                breakdown_filename_uuid = breakdown_filename.split('.')[0]

                preprocessed_document = self.preprocess_file(filepath)

                if self.is_file_already_processed(breakdown_filename_uuid, is_breakdown=True):
                    print(f'File {breakdown_filename_uuid} already preprocessed')
                    continue 

                self.append_to_already_preprocessed_documents_log(
                    file_uuid=file.split('.')[0], 
                    file_uuid_breakdown=breakdown_filename_uuid,
                    etl_timestamp=datetime.now(), 
                )

                self.save_preprocessed_documents(preprocessed_document, breakdown_filename_uuid)

            for to_delete_file in os.listdir(self.single_page_folder):
                os.remove(os.path.join(self.single_page_folder, to_delete_file))
                

    def execute(self, context):
        self.metadata = self.get_already_preprocessed_metadata_from_csv()
        self.process_files()
        self.metadata.to_csv(self.preprocess_log_path, index=False)