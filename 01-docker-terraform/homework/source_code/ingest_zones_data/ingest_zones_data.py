#!/usr/bin/env python
# coding: utf-8

import click
import pandas as pd
from sqlalchemy import create_engine
from tqdm.auto import tqdm
import os

@click.command()
@click.option('--target-table', default='yellow_taxi_data', help='Target table name')
@click.option('--chunksize', default=100000, type=int, help='Chunk size for reading CSV')

def run(target_table, chunksize):
    """Ingest Zone NYC taxi data into PostgreSQL database."""
    url = os.environ['URL_ZONES']
    pg_user = os.environ['USER_PSQL']
    pg_pass = os.environ['PASS_PSQL']
    pg_host = os.environ['HOST_PSQL']
    pg_port = os.environ['PORT_PSQL_LOCAL']
    pg_db = os.environ['DB_PSQL']
    first = True
    engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')

    df_iter = pd.read_csv(
        url,
        iterator=True,
        chunksize=chunksize,
    )

    for df_chunk in tqdm(df_iter):
        if first:
            df_chunk.head(0).to_sql(
                name=target_table,
                con=engine,
                if_exists='replace',
                index=False
            )
            first = False

        df_chunk.to_sql(
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
