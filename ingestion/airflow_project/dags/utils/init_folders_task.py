import os
import pandas as pd 

from datetime import datetime
from typing import Dict, List, Set, Union

from airflow.models.baseoperator import BaseOperator

class InitFoldersTask(BaseOperator):
    def __init__(
            self, 
            task_id: str,
            folders: Union[str, List[str]], 
            **kwargs
        ) -> None:

        super(InitFoldersTask, self).__init__(task_id=task_id, **kwargs)
        
        self.folders = [folders] if isinstance(folders, str) else folders


    def execute(self, context):
        for folder in self.folders:
            if not os.path.exists(folder):
                print(f'Folder: {folder} does not exists, creating it.')
                os.makedirs(folder) 