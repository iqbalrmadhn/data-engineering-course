"""Pipeline to ingest NYC Taxi data from the Zoomcamp API."""

import dlt
from dlt.sources.rest_api import rest_api_source

BASE_URL = "https://us-central1-dlthub-analytics.cloudfunctions.net/data_engineering_zoomcamp_api"


def taxi_source():
    """
    Create a dlt source for the NYC Taxi REST API.
    """
    return rest_api_source({
        "client": {
            "base_url": BASE_URL,
        },
        "resource_defaults": {
            "write_disposition": "append",
        },
        "resources": [
            {
                "name": "nyc_taxi_data",
                "endpoint": {
                    "path": "",  # root path
                    "params": {
                        "page": 1,
                    },
                    "data_selector": ".",  # entire JSON response
                    "paginator": {
                        "type": "page",
                        "parameter": "page",
                        "start": 1,
                        "increment": 1,
                        # Stop when API returns an empty list
                        "stop_condition": lambda page, data: len(data) == 0,
                    },
                },
            },
        ],
    })


if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="taxi_pipeline",
        destination="duckdb",
        dataset_name="nyc_taxi_data",
        progress="log",
    )

    # Load NYC Taxi data into DuckDB
    load_info = pipeline.run(taxi_source())
    print(load_info)
