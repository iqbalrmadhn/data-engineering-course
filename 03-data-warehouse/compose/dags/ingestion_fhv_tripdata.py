from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

import os
import time
import fnmatch
import requests
import pandas as pd
from google.cloud import storage
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded

INIT_URL = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/'
MAX_RETRIES = 3
RETRY_DELAY = 5

def upload_to_gcs(bucket_name, folder_gcs, folder_local_file):
    pattern = f"fhv_tripdata_2019-*.csv.gz"
    client = storage.Client.from_service_account_json(
        Variable.get("api_key_gc"),
        project=Variable.get("project_id_gcp")
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
        if fnmatch.fnmatch(file_name, pattern):
            full_path = os.path.join(folder_local_file, file_name)
            object_name = folder_gcs + file_name
            blob = bucket.blob(object_name)
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    blob.upload_from_filename(full_path,timeout=300)
                    print(f"Uploaded to GCS: {object_name}")
                    break
                except (ServiceUnavailable, DeadlineExceeded, requests.exceptions.ConnectionError) as e:
                    print(f"Attempt {attempt} failed for {file_name}: {e}")
                    if attempt < RETRY_DELAY:
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"Failed to upload {file_name} after {MAX_RETRIES} attempts.")
            print(f"GCS: {object_name}")

def download_data_from_web():
    for i in range(0, 12):
        month_str = f"{i+1:02d}"

        # csv file_name
        file_name = f"fhv_tripdata_2019-{month_str}.csv.gz"
        tmp_dir = "/opt/airflow/data/file_tmp"
        local_csv_path = os.path.join(tmp_dir, file_name)

        if os.path.exists(local_csv_path):
            print(f"{file_name} already exists, skipping...")
        else:
            request_url = f"{INIT_URL}/fhv/{file_name}"
            r = requests.get(request_url)
            if r.status_code != 200:
                raise Exception(f"Failed to download {request_url} (status {r.status_code})")

            with open(local_csv_path, "wb") as f:
                f.write(r.content)
            print(f"Local: {local_csv_path}")

with DAG(
    dag_id="ingest_data_fhv_tripdata",
    schedule=None,
    catchup=False,
):
    download_data = PythonOperator(
        task_id="download_data",
        python_callable=download_data_from_web,
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

    load_csv_to_bq = GCSToBigQueryOperator(
        task_id="write_data",
        bucket=Variable.get("bucket_name"),
        source_objects=[Variable.get("folder_gcs")+"fhv_tripdata_2019*.csv.gz"],
        destination_project_dataset_table=f"{Variable.get('project_id_gcp')}.fhv.fhv_trip_data_external",
        source_format="CSV",
        compression="GZIP", 
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        gcp_conn_id="gc",
    )

    download_data >> upload_file >> load_csv_to_bq
