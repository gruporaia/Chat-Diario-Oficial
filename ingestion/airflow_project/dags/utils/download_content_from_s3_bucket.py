import os
import uuid
import pandas as pd 
import time 
import shutil 

from typing import Dict

from datetime import datetime, timedelta
from airflow.hooks.S3_hook import S3Hook

from airflow.models.baseoperator import BaseOperator


class DownloadContentFromS3(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            bucket_name: str, 
            s3_key_to_local_filename: Dict[str,str],
            s3_conn_id: str,
            **kwargs
        ) -> None:

        super(DownloadContentFromS3, self).__init__(task_id=task_id, **kwargs)
        
        self.bucket_name = bucket_name
        self.s3_conn_id = s3_conn_id
        self.s3_key_to_local_filename = s3_key_to_local_filename
        self.hook = None
        self.max_move_retries = 10

    def init_hook(self):
        return S3Hook(self.s3_conn_id)


    def s3_bucket_exists(self):
        return self.hook.check_for_bucket(self.bucket_name)


    def download_from_s3(self) -> None:
        for key, local_filename in self.s3_key_to_local_filename.items():
            local_file_path = os.path.dirname(local_filename)
            
            if not self.hook.check_for_key(key, self.bucket_name):
                print(f'Key {key} does not exists in bucket {self.bucket_name}')
                continue 
            
            filename = self.hook.download_file(
                key=key, 
                bucket_name=self.bucket_name, 
                local_path=local_file_path,
                preserve_file_name=True,
            )

            shutil.move(filename, local_filename)
            shutil.rmtree(os.path.dirname(filename))


    def execute(self, context):
        self.hook = self.init_hook()
        if self.s3_bucket_exists():
            self.download_from_s3()
        else:
            print('Bucket does not exists')