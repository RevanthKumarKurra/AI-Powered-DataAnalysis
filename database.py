import os 

from dotenv import load_dotenv
load_dotenv()

import duckdb


connection = duckdb.connect()
connection.execute("INSTALL httpfs; LOAD httpfs;")

access_key = os.getenv("AWS_ACCESS_KEY_ID")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
endpoint = os.getenv("ENDPOINT_URL")

endpoint = endpoint.removeprefix("https://").removesuffix("/")

def duckdb_connect():
    connection.execute(f"""
    CREATE SECRET r2_secret (
    TYPE S3,
    KEY_ID {access_key},
    SECRET {secret_key},
    REGION 'auto',
    ENDPOINT '{endpoint}',
    URL_STYLE 'path'
    );
    """)

    return connection

