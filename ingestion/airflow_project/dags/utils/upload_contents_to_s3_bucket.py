import os
import uuid
import pandas as pd 
import time 

from typing import Dict
from datetime import datetime, timedelta
from airflow.hooks.S3_hook import S3Hook

from airflow.models.baseoperator import BaseOperator


class UploadContentsToS3(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            bucket_name: str, 
            s3_conn_id: str,
            s3_path_to_local_filepath: Dict[str, str],
            **kwargs
        ) -> None:

        super(UploadContentsToS3, self).__init__(task_id=task_id, **kwargs)
        
        self.bucket_name = bucket_name
        self.s3_conn_id = s3_conn_id
        self.s3_path_to_local_filepath = s3_path_to_local_filepath


    def init_hook(self):
        return S3Hook(self.s3_conn_id)


    def s3_bucket_exists(self):
        return self.hook.check_for_bucket(self.bucket_name)


    def create_bucket(self):
        self.hook.create_bucket(self.bucket_name)


    def upload_to_s3(self) -> None:
        for s3_key, local_obj in self.s3_path_to_local_filepath.items():
            print(f'Loading object {local_obj} into S3 bucket {self.bucket_name}/{s3_key}')
            if os.path.isfile(local_obj):
                print(f'Loading file {local_obj} into S3 bucket {self.bucket_name}/{s3_key}')
                self.hook.load_file(
                    filename=local_obj, 
                    key=s3_key, 
                    bucket_name=self.bucket_name, 
                    replace=True
                )

            elif os.path.isdir(local_obj):
                print(f'Loading folder {local_obj} into S3 bucket {self.bucket_name}/{s3_key}')
                for file in os.listdir(local_obj):
                    if os.path.isfile(os.path.join(local_obj, file)):
                        self.hook.load_file(
                            filename=os.path.join(local_obj, file), 
                            key=os.path.join(s3_key, file), 
                            bucket_name=self.bucket_name, 
                            replace=True
                        )


    def execute(self, context):
        self.hook = self.init_hook()

        if not self.s3_bucket_exists():
            self.create_bucket()
        
        self.upload_to_s3()
