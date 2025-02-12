import os
import uuid
import pandas as pd 
import time 

from datetime import datetime, timedelta
from airflow.hooks.S3_hook import S3Hook

from airflow.models.baseoperator import BaseOperator


class UploadContentToS3(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            bucket_name: str, 
            local_folder_path: str,
            s3_conn_id: str,
            local_file_name: str = None,
            s3_folder_path: str = None,
            **kwargs
        ) -> None:

        super(UploadContentToS3, self).__init__(task_id=task_id, **kwargs)
        
        self.bucket_name = bucket_name
        self.local_folder_path = local_folder_path
        self.s3_conn_id = s3_conn_id
        self.local_file_name = local_file_name
        self.s3_folder_path = s3_folder_path
        self.hook = self.init_hook()

    def init_hook(self):
        return S3Hook(self.s3_conn_id)


    def s3_bucket_exists(self):
        return self.hook.check_for_bucket(self.bucket_name)


    def create_bucket(self):
        self.hook.create_bucket(self.bucket_name)


    def upload_to_s3(self) -> None:
        if self.local_file_name is not None:
            self.hook.load_file(
                filename=os.path.join(self.local_folder_path, self.local_file_name), 
                key=self.local_file_name if self.s3_folder_path is None else os.path.join(self.s3_folder_path, self.local_file_name), 
                bucket_name=self.bucket_name, 
                replace=True
            )
        else:
            for file in os.listdir(self.local_folder_path):
                self.hook.load_file(
                    filename=os.path.join(self.local_folder_path, file), 
                    key=file if self.s3_folder_path is None else os.path.join(self.s3_folder_path, file), 
                    bucket_name=self.bucket_name, 
                    replace=True
                )


    def execute(self, context):
        if not self.s3_bucket_exists():
            self.create_bucket()
        self.upload_to_s3()
