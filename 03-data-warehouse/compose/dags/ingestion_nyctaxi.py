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
from google.cloud.exceptions import NotFound
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

INIT_URL = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/'
MAX_RETRIES = 3
RETRY_DELAY = 5

def upload_to_gcs(bucket_name, folder_gcs, folder_local_file, year, service):
    pattern = f"{service}_tripdata_{year}-*.csv.gz"
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

def download_data_from_web(year, month, service):
    for i in range(0, month):
        month_str = f"{i+1:02d}"

        # csv file_name
        # file_name = f"{service}_tripdata_{year}-{month_str}.csv"
        file_name = f"{service}_tripdata_{year}-{month_str}.csv.gz"
        tmp_dir = "/opt/airflow/data/file_tmp"
        local_csv_path = os.path.join(tmp_dir, file_name)

        if os.path.exists(local_csv_path):
            print(f"{file_name} already exists, skipping...")
        else:
            request_url = f"{INIT_URL}/{service}/{file_name}"
            r = requests.get(request_url)
            if r.status_code != 200:
                raise Exception(f"Failed to download {request_url} (status {r.status_code})")

            with open(local_csv_path, "wb") as f:
                f.write(r.content)
            print(f"Local: {local_csv_path}")

def csv_to_bq():
    credentials = service_account.Credentials.from_service_account_file(
        Variable.get("api_key_gc")
    )
    client = bigquery.Client(
        project=Variable.get("project_id_gcp"),
        credentials=credentials
    )

    stg_table_id = f"{Variable.get('project_id_gcp')}.nyc_taxi.stg_{Variable.get('data_service')}_trip_data"
    table_id = f"{Variable.get('project_id_gcp')}.nyc_taxi.{Variable.get('data_service')}_trip_data"
    csv_folder = "/opt/airflow/data/file_tmp"
    pattern = f"{Variable.get('data_service')}_tripdata_{Variable.get('data_year')}-*.csv.gz"

    if Variable.get("data_service") == "yellow":
        schema = [
            bigquery.SchemaField("VendorID", "INT64"),
            bigquery.SchemaField("tpep_pickup_datetime", "TIMESTAMP"),
            bigquery.SchemaField("tpep_dropoff_datetime", "TIMESTAMP"),
            bigquery.SchemaField("passenger_count", "INT64"),
            bigquery.SchemaField("trip_distance", "FLOAT64"),
            bigquery.SchemaField("RatecodeID", "INT64"),
            bigquery.SchemaField("store_and_fwd_flag", "STRING"),
            bigquery.SchemaField("PULocationID", "INT64"),
            bigquery.SchemaField("DOLocationID", "INT64"),
            bigquery.SchemaField("payment_type", "INT64"),
            bigquery.SchemaField("fare_amount", "FLOAT64"),
            bigquery.SchemaField("extra", "FLOAT64"),
            bigquery.SchemaField("mta_tax", "FLOAT64"),
            bigquery.SchemaField("tip_amount", "FLOAT64"),
            bigquery.SchemaField("tolls_amount", "FLOAT64"),
            bigquery.SchemaField("improvement_surcharge", "FLOAT64"),
            bigquery.SchemaField("total_amount", "FLOAT64"),
            bigquery.SchemaField("congestion_surcharge", "FLOAT64"),
            bigquery.SchemaField("ds", "DATE"),
        ]
        pickup_col = "tpep_pickup_datetime"
        dropoff_col = "tpep_dropoff_datetime"
    else:
        schema = [
            bigquery.SchemaField("VendorID", "INTEGER"),
            bigquery.SchemaField("lpep_pickup_datetime", "TIMESTAMP"),
            bigquery.SchemaField("lpep_dropoff_datetime", "TIMESTAMP"),
            bigquery.SchemaField("store_and_fwd_flag", "STRING"),
            bigquery.SchemaField("RatecodeID", "FLOAT"),
            bigquery.SchemaField("PULocationID", "INTEGER"),
            bigquery.SchemaField("DOLocationID", "INTEGER"),
            bigquery.SchemaField("passenger_count", "FLOAT"),
            bigquery.SchemaField("trip_distance", "FLOAT"),
            bigquery.SchemaField("fare_amount", "FLOAT"),
            bigquery.SchemaField("extra", "FLOAT"),
            bigquery.SchemaField("mta_tax", "FLOAT"),
            bigquery.SchemaField("tip_amount", "FLOAT"),
            bigquery.SchemaField("tolls_amount", "FLOAT"),
            bigquery.SchemaField("ehail_fee", "FLOAT"),
            bigquery.SchemaField("improvement_surcharge", "FLOAT"),
            bigquery.SchemaField("total_amount", "FLOAT"),
            bigquery.SchemaField("payment_type", "FLOAT"),
            bigquery.SchemaField("trip_type", "FLOAT"),
            bigquery.SchemaField("congestion_surcharge", "FLOAT"),
            bigquery.SchemaField("ds", "DATE"),
        ]
        pickup_col = "lpep_pickup_datetime"
        dropoff_col = "lpep_dropoff_datetime"

    # skip_months = {"2019-01", "2019-02", "2019-03", "2019-04", "2019-05", "2019-06", "2019-07", "2019-08", "2019-09", "2019-10", "2019-11"}
    skip_months = {}
    for file_name in os.listdir(csv_folder):
        if fnmatch.fnmatch(file_name, pattern):
            if any(month in file_name for month in skip_months):
                print(f"Skipping file: {file_name}")
                continue
            file_path = os.path.join(csv_folder, file_name)
            print(f"Loading file: {file_path}")

            df = pd.read_csv(file_path, index_col=False, compression="gzip")
            total_row = len(df)
            df[pickup_col] = pd.to_datetime(df[pickup_col])
            df[dropoff_col] = pd.to_datetime(df[dropoff_col])

            base_name = os.path.basename(file_name)
            date_str = base_name.replace(f"{Variable.get('data_service')}_tripdata_", "").replace(".csv.gz", "")
            date_col = datetime.strptime(date_str, "%Y-%m").date()
            df["ds"] = date_col

            # write staging
            load_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition="WRITE_TRUNCATE",
                create_disposition="CREATE_IF_NEEDED",
            )

            load_job = client.load_table_from_dataframe(
                df,
                stg_table_id,
                job_config=load_config
            )

            load_job.result()
            print("Staging load complete.")

            try:
                client.get_table(table_id)
                table_exists = True
            except NotFound:
                table_exists = False

            if table_exists:
                delete_query = f"""
                DELETE FROM `{table_id}`
                WHERE ds = '{date_col}'
                """
                delete_job = client.query(delete_query)
                delete_job.result()
                print("Existing partitions deleted (if any).")
            else:
                print("Target table does not exist. Skipping delete step.")

            if table_exists:    
                insert_query = f"""
                INSERT INTO `{table_id}`
                SELECT * FROM `{stg_table_id}`
                """
                insert_job = client.query(insert_query)
                insert_job.result()
            else:
                create_table = bigquery.LoadJobConfig( 
                    schema=schema, 
                    write_disposition="WRITE_APPEND", 
                    create_disposition="CREATE_IF_NEEDED", 
                    time_partitioning=bigquery.TimePartitioning( 
                        type_=bigquery.TimePartitioningType.DAY, field="ds" 
                        ) 
                    )

                create_table_job = client.load_table_from_dataframe(
                    df,
                    table_id,
                    job_config=create_table
                )

                create_table_job.result()
                print("First write table")

            count_query = f"""
            SELECT COUNT(1) AS partition_rows
            FROM `{table_id}`
            WHERE ds = '{date_col}'
            """
            count_job = client.query(count_query)
            for row in count_job:
                print(f"total row csv = {total_row}, total data in bigquery = {row.partition_rows} for ds {date_col}")
            
            del(df)
            print(f"file {file_name} loaded successfully")

    print("All csv files loaded successfully.")

with DAG(
    dag_id="ingest_data_nyc_taxi",
    schedule=None,
    catchup=False,
):
    download_data = PythonOperator(
        task_id="download_data",
        python_callable=download_data_from_web,
        op_kwargs={
            "year": Variable.get("data_year"),
            "month": int(Variable.get("data_last_month")),
            "service": Variable.get("data_service"),
            },
    )

    upload_file = PythonOperator(
        task_id="upload_file",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket_name": Variable.get("bucket_name"),
            "folder_gcs": Variable.get("folder_gcs"),
            "folder_local_file": "/opt/airflow/data/file_tmp/",
            "year": Variable.get("data_year"),
            "service": Variable.get("data_service"),
            },
    )

    load_csv_to_bq = GCSToBigQueryOperator(
        task_id="write_data",
        bucket=Variable.get("bucket_name"),
        source_objects=[Variable.get("folder_gcs")+f"{Variable.get('data_service')}_tripdata_{Variable.get('data_year')}*.csv.gz"],
        destination_project_dataset_table=f"{Variable.get('project_id_gcp')}.nyc_taxi.{Variable.get('data_service')}_trip_data_external",
        source_format="CSV",
        compression="GZIP", 
        write_disposition="WRITE_APPEND",  # or WRITE_TRUNCATE
        create_disposition="CREATE_IF_NEEDED",
        gcp_conn_id="gc",
    )

    # load_csv_to_bq = PythonOperator(
    #     task_id="write_table",
    #     python_callable=csv_to_bq,
    # )

    download_data >> upload_file >> load_csv_to_bq
    # download_data >> load_csv_to_bq
