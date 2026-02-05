from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

import os
import requests
import pandas as pd
from google.cloud import storage

"""
Pre-reqs: 
1. `pip install pandas pyarrow google-cloud-storage`
2. Set GOOGLE_APPLICATION_CREDENTIALS to your project/service-account key
3. Set GCP_GCS_BUCKET as your bucket or change default value of BUCKET
"""

INIT_URL = 'https://d37ci6vzurychx.cloudfront.net/trip-data'

def upload_to_gcs(bucket_name, folder_gcs, folder_local_file):
    client = storage.Client.from_service_account_json(
        Variable.get("api_key_gc"),
        project="de-course-484302"
        )
    # client = storage.Client()
    bucket = client.lookup_bucket(bucket_name)
    if not bucket:
        bucket = client.create_bucket(bucket_name)
        print(f"Created bucket {bucket.name}")
    else:
        print(f"Bucket {bucket_name} already exists")
    bucket = client.bucket(bucket_name)

    for file_name in os.listdir(folder_local_file):
        if file_name.endswith(".parquet"):
            full_path = os.path.join(folder_local_file, file_name)
            object_name = folder_gcs + file_name
            blob = bucket.blob(object_name)
            blob.upload_from_filename(full_path)
            print(f"GCS: {object_name}")

def download_data_from_web(year, month, service):
    for i in range(0, month):
        month_str = f"{i+1:02d}"

        # csv file_name
        file_name = f"{service}_tripdata_{year}-{month_str}.parquet"
        tmp_dir = "/opt/airflow/data/file_tmp"
        local_csv_path = os.path.join(tmp_dir, file_name)

        request_url = f"{INIT_URL}/{file_name}"
        r = requests.get(request_url)
        if r.status_code != 200:
            raise Exception(f"Failed to download {request_url} (status {r.status_code})")

        with open(local_csv_path, "wb") as f:
            f.write(r.content)
        print(f"Local: {local_csv_path}")

with DAG(
    dag_id="web_to_gcs",
    schedule=None,
    catchup=False,
):
    download_data = PythonOperator(
        task_id="download_data",
        python_callable=download_data_from_web,
        op_kwargs={
            "year": "2024",
            "month":6,
            "service":"yellow",
            },
    )

    upload_file = PythonOperator(
        task_id="upload_file",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket_name": Variable.get("bucket_name"),
            "folder_gcs": Variable.get("folder_gcs"),
            "folder_local_file": "/opt/airflow/data/file_tmp/",
            },
    )

    download_data >> upload_file
