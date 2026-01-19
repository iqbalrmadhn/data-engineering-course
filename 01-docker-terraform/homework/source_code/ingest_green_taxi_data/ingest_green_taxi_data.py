#!/usr/bin/env python
# coding: utf-8

import click
import pandas as pd
from sqlalchemy import create_engine
import os

dtype = {
    "VendorID": "Int64",
    "store_and_fwd_flag": "string",
    "RatecodeID": "Int64",
    "RatecodeID": "Int64",
    "store_and_fwd_flag": "string",
    "PULocationID": "Int64",
    "DOLocationID": "Int64",
    "passenger_count": "Int64",
    "trip_distance": "float64",
    "fare_amount": "float64",
    "extra": "float64",
    "mta_tax": "float64",
    "tip_amount": "float64",
    "tolls_amount": "float64",
    "ehail_fee": "float64",
    "improvement_surcharge": "float64",
    "total_amount": "float64",
    "payment_type": "string",
    "trip_type": "string",
    "congestion_surcharge": "float64",
    "cbd_congestion_fee": "float64",
}

parse_dates = [
    "lpep_pickup_datetime",
    "lpep_dropoff_datetime"
]

@click.command()
@click.option('--target-table', default='green_taxi_data', help='Target table name')

def run(target_table):
    """Ingest NYC taxi data into PostgreSQL database."""
    url = os.environ['URL_GREEN_TAXI']
    pg_user = os.environ['USER_PSQL']
    pg_pass = os.environ['PASS_PSQL']
    pg_host = os.environ['HOST_PSQL']
    pg_port = os.environ['PORT_PSQL_LOCAL']
    pg_db = os.environ['DB_PSQL']
    first = True
    engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')

    df_raw = pd.read_parquet(
        url,
        engine="pyarrow"
    )
    
    for col in ["lpep_pickup_datetime","lpep_dropoff_datetime",]:
        if col in df_raw.columns:
            df_raw[col] = pd.to_datetime(df_raw[col], errors="coerce")

    df_raw = df_raw.astype(dtype)

    if first:
        df_raw.head(0).to_sql(
            name=target_table,
            con=engine,
            if_exists='replace',
            index=False
        )
        first = False

    df_raw.to_sql(
        name=target_table,
        con=engine,
        if_exists='append',
        index=False
    )

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        raise Exception(f"got error: {e}")