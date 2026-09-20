import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()
import pandas as pd

s3 = boto3.client(
    service_name="s3",
    endpoint_url=os.getenv("ENDPOINT_URL"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="auto",
)


def upload_file_s3(path,name):
    s3.upload_file(path,"mybucket",name)



def getdiscribtions(pathfile,filename):

    try:
        if filename.lower().endswith(".csv"):
            file = pd.read_csv(pathfile)

        elif filename.lower().endswith(".xlsx"):
            file = pd.read_excel(pathfile)

        else:
            return "Only CSV and XLSX files are supported"

    except Exception as e:
        return f"Failed to read file: {e}"


    file = pd.read_csv(pathfile)
    s3_bucket_path = f"s3://mybucket/{filename}"

    schema = {"filename":s3_bucket_path,
                "rows":len(file),
                "columns":[]}


    for col in file.columns:

        dtype = str(file[col].dtype)

        if dtype == object:
            file[col] = file[col].apply(lambda x:x.lower())

            schema['columns'].append(
                    {
                    "name":col,
                    "dtype":str(file[col].dtype),
                })
                               
        else:

                schema['columns'].append(
                {
                    "name":col,
                    "dtype":str(file[col].dtype),
                }
            )
    return schema




def file_exist(filename:str,bucket:str="mybucket"):

    try:
        s3.head_object(Bucket = bucket,Key = filename)
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            print(f"An error occurred: {e}")
            raise