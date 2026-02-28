"""@bruin

name: ingestion.trips
connection: duckdb-default

materialization:
  type: table
  strategy: append
image: python:3.11

secrets:
  - key: duckdb-default
    inject_as: duckdb-default

columns:
  - name: pickup_datetime
    type: timestamp
    description: When the meter was engaged
  - name: dropoff_datetime
    type: timestamp
    description: When the meter was disengaged

@bruin"""

import os
import json
import pandas as pd
from datetime import datetime

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def generate_month_range(start_date: str, end_date: str):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    months = []
    current = start.replace(day=1)
    while current <= end:
        months.append((current.year, current.month))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def materialize():
    start_date = os.environ["BRUIN_START_DATE"]
    end_date = os.environ["BRUIN_END_DATE"]
    taxi_types = json.loads(os.environ["BRUIN_VARS"]).get("taxi_types", ["yellow"])

    months = generate_month_range(start_date, end_date)
    dataframes = []

    for taxi_type in taxi_types:
        for year, month in months:
            month_str = f"{month:02d}"
            url = f"{BASE_URL}/{taxi_type}_tripdata_{year}-{month_str}.parquet"
            try:
                print(f"Downloading: {url}")
                df = pd.read_parquet(url, engine="pyarrow")
                df = df.rename(
                        columns={
                            "tpep_pickup_datetime": "pickup_datetime",
                            "tpep_dropoff_datetime": "dropoff_datetime",
                            "PULocationID": "pickup_location_id",
                            "DOLocationID": "dropoff_location_id",
                        }
                    )
                df["taxi_type"] = taxi_type
                
                dataframes.append(df)
            except Exception as e:
                print(f"Skipping {url} due to error: {e}")

    if not dataframes:
        raise ValueError("No data downloaded for the given date range.")

    final_dataframe = pd.concat(dataframes, ignore_index=True)
    return final_dataframe
