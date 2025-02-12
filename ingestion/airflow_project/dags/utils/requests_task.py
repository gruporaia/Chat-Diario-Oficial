import os
import uuid
import json 
import requests 
import time 

import pandas as pd 

from datetime import datetime, timedelta
from random import random 
from typing import Dict, List

from airflow.models.baseoperator import BaseOperator


class RequestGazettesTask(BaseOperator):
    template_fields = ('pull_start_date', 'pull_end_date')

    def __init__(
            self, 
            task_id: str,
            api_base_url: str, 
            file_ingestion_metadata_path: str,
            max_size_per_request: int,
            pull_start_date: str,
            pull_end_date: str,
            download_folder: str,
            territory_ids: str,
            **kwargs
        ) -> None:

        super(RequestGazettesTask, self).__init__(task_id=task_id, **kwargs)
        
        self.download_folder = download_folder
        self.api_base_url = api_base_url
        self.file_ingestion_metadata_path = file_ingestion_metadata_path
        self.max_size_per_request = max_size_per_request
        self.pull_start_date = pull_start_date
        self.pull_end_date = pull_end_date
        self.territory_ids = territory_ids

    def get_payload(
        self,
        start_date: str, 
        end_date: str, 
        territory_ids: str, # IBGE city code
        size: int=1, # Number of documents to fetch from the API
        excerpt_size: int=500, # Maximum number of characters that an excerpt should display
        offset: int=0 # Number of search results to be skipped in the response
    ) -> Dict:
        return {
            "size": size, 
            "excerpt_size": excerpt_size,
            "published_since": start_date,
            "published_until": end_date,
            "territory_ids": territory_ids,
            "offset": offset,
        }


    def manage_file_metadata(self, file_metadata: List[Dict]):
        print('Managing URL log')
        if not os.path.isfile(self.file_ingestion_metadata_path) or pd.read_csv(self.file_ingestion_metadata_path).empty:
            metadata = pd.DataFrame(columns=['url', 'file_uuid', 'etl_timestamp'])
        else:
            metadata = pd.read_csv(self.file_ingestion_metadata_path)
        
        urls = set(metadata['url'].to_list())

        new_downloads = [
            file 
            for file in file_metadata
            if file['url'] not in urls 
        ]

        for file in file_metadata:
            if file['url'] in urls:
                etl_timestamp = metadata[metadata['url'] == file['url']]['etl_timestamp'].iloc[0]
                print(f'Skipping text url: {file["url"]} because it was already downloaded in {etl_timestamp}')

        metadata = pd.concat([metadata, pd.DataFrame(new_downloads)])
        metadata.to_csv(self.file_ingestion_metadata_path, index=False)
        
        return new_downloads


    def get_total_gazettes(self):
        payload = self.get_payload(self.pull_start_date, self.pull_end_date, self.territory_ids, size=1)
        request = requests.get(self.api_base_url, params=payload)
        return json.loads(request.content)['total_gazettes']


    def parse_request_content(self,request):
        return [
            {
                'url': result['url'],
                'edition': result['edition'],
                'date': result['date'],
                'is_extra_edition': result['is_extra_edition'],
                'city_code': result['territory_id']
            }
            for result in json.loads(request.content)['gazettes']
        ]


    def create_files_metadata(self, gazettes: List[Dict]) -> List[Dict]:
        etl_timestamp = datetime.now()
        return [ 
            {
                'url': gazette['url'], 
                'file_uuid': f"{gazette['city_code']}_{gazette['date']}_{gazette['edition']}{'_extra_edition' if gazette['is_extra_edition'] else ''}",
                'etl_timestamp': etl_timestamp,
                'city_code': gazette['city_code'],
            } 
            for gazette in gazettes
        ]


    def download_text_files(self, files_metadata: List[Dict]):
        if not os.path.exists(self.download_folder):
            print(f'Download folder: {self.download_folder} does not exists, creating it.')
            os.makedirs(self.download_folder)

        for metadata in files_metadata:
            request = requests.get(metadata['url'])
            file_uuid = metadata['file_uuid']

            with open(os.path.join(self.download_folder, file_uuid) + '.pdf', 'wb') as f:
                f.write(request.content)


    def pull_gazettes(self):
        total_gazettes = self.get_total_gazettes()
        print(f'Total number of Gazettes: {total_gazettes}')

        number_of_requests = total_gazettes // self.max_size_per_request + (1 if total_gazettes % self.max_size_per_request != 0 else 0)
        results = []
        for i in range(number_of_requests):
            offset = i * self.max_size_per_request

            print(f'log request call: {self.api_base_url}, params: {self.get_payload(self.pull_start_date, self.pull_end_date, self.territory_ids, offset=offset)}')
            
            request = requests.get(self.api_base_url, params=self.get_payload(self.pull_start_date, self.pull_end_date, self.territory_ids, size=self.max_size_per_request, offset=offset))
            
            results.extend(self.parse_request_content(request))
            
            time.sleep(10 * random())

        return results
    
    
    def init_folders(self):
        if not os.path.exists(os.path.dirname(self.file_ingestion_metadata_path)):
            print(f'DB folder: {os.path.dirname(self.file_ingestion_metadata_path)} does not exists, creating it.')
            os.makedirs(os.path.dirname(self.file_ingestion_metadata_path))


    def execute(self, context):
        print(f'Running for start_date: {self.pull_start_date}, end_date: {self.pull_end_date}')
        self.init_folders()

        gazettes = self.pull_gazettes()
        files_metadata = self.create_files_metadata(gazettes)
        new_downloads = self.manage_file_metadata(files_metadata)
        
        self.download_text_files(new_downloads)
        return