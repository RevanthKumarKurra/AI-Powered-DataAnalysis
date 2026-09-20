from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import uvicorn

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from database import duckdb_connect
from s3_storage import (
    getdiscribtions,
    upload_file_s3,
    file_exist
)



app = FastAPI(title="AI CSV Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STORAGE_PATH = "./storage"
CHART_PATH = "./generated/charts"

os.makedirs(STORAGE_PATH, exist_ok=True)
os.makedirs(CHART_PATH, exist_ok=True)



connect = duckdb_connect()



llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
    max_tokens=None,
    timeout=None
)




def get_file_description(path=STORAGE_PATH):

    file_description = []

    for filename in os.listdir(path):

        full_path = os.path.join(path, filename)

        if not filename.lower().endswith(".csv"):
            continue

        description = getdiscribtions(
            full_path,
            filename
        )

        file_description.append(description)

        # Upload to S3 if required
        if not file_exist(filename):

            print(f"Uploading {filename}")

            upload_file_s3(
                full_path,
                filename
            )

    return file_description


def save_uploaded_file(contents: bytes, filename: str):
    filename = os.path.basename(filename)

    if filename.lower().endswith(".csv"):
        filepath = os.path.join(STORAGE_PATH, filename)

        with open(filepath, "wb") as f:
            f.write(contents)

        df = pd.read_csv(filepath)

        df.drop_duplicates(inplace=True, ignore_index=True)
        df.dropna(inplace=True, ignore_index=True)

        df.to_csv(filepath, index=False)

        return [filename]

    if filename.lower().endswith((".xlsx", ".xls")):

        excel_path = os.path.join(STORAGE_PATH, filename)

        with open(excel_path, "wb") as f:
            f.write(contents)

        excel_file = pd.ExcelFile(excel_path)

        generated_files = []
        base_name = os.path.splitext(filename)[0]

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_path,sheet_name=sheet_name)
            df.drop_duplicates(inplace=True, ignore_index=True)
            df.dropna(inplace=True, ignore_index=True)

            clean_sheet_name = "".join(
                c if c.isalnum() or c in "_-" else "_"
                for c in sheet_name
            )

            csv_filename = f"{base_name}_{clean_sheet_name}.csv"

            csv_path = os.path.join(STORAGE_PATH,csv_filename)

            df.to_csv(csv_path,index=False)
            generated_files.append(csv_filename)

        return generated_files

    raise ValueError(
        "Only CSV, XLSX and XLS files are supported."
    )

@tool
def execute_sql(query: str):
    """
    Execute DuckDB SQL query and return the result.
    """

    try:

        result = connect.execute(query).fetchdf()

        explanation = llm.invoke(f"""
                SQL:{query}
                Query result:{result.to_string(index=False)}
                
                Explain the result shown in the chart.
                Mention important trends, highest/lowest values,
                percentages if relevant, and avoid making claims
                not supported by the data.""")

        return {
            "type": "table",
            "query": query,
            "data": result.to_dict(orient="records"),
            "columns": list(result.columns),
            "explanation": explanation.content}

    except Exception as exp:

        return {
            "type": "error",
            "error": str(exp)
        }



@tool
def generate_visualization(query: str, code: str):
    """
    Execute SQL and generate a matplotlib visualization.
    """

    try:

        df = connect.execute(query).fetchdf()
        exec(code)

        filename = f"{uuid.uuid4().hex}.png"

        filepath = os.path.join(CHART_PATH,filename)

        plt.savefig(filepath,bbox_inches="tight",dpi=150)
        plt.close()

        explanation = llm.invoke(
            f"""
            SQL:{query}
                    Query result:{df.to_string(index=False)}
                    
                    Explain the result shown in the chart.
                    Mention important trends, highest/lowest values,
                    percentages if relevant, and avoid making claims
                    not supported by the data.""")

        return {
            "type": "chart",
            "query": query,
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns),
            "chart_url": f"/charts/{filename}",
            "explanation": explanation.content
        }

    except Exception as exp:

        plt.close()

        return {
            "type": "error",
            "error": str(exp)
        }



tools = [execute_sql,generate_visualization]
llm_tool = llm.bind_tools(tools)

class QuestionRequest(BaseModel):
    question: str


def get_response(question: str):


    file_description = get_file_description()

    messages = [
        SystemMessage(content=f"""You are an a high experienced duckdb sql assistnat where your task
        is to understand the text that which was provied by the user and you have all
        the metadate of the csv files that user require with their path and columns and its
        data type where your are an a sql assitant you are professional in ducksql that which
        will take csv file path instead of the table and remaing all will be same for example
        
        Example DuckDB Query: "SELECT * 
                               FROM read_csv_auto(s3://mybucket/categories.csv)
                               LIMIT 10" 
                               
        here you will pass the csv file and path read different read_csv_auto like this 
        you need to query that their might joints also where you need to pass two csv files instead 
        of tabel names  etc if you get any plot like design query in such a way that if it given to
        any ploting module it should execute  and result like that fit and create.  here is the users metadata
        {file_description}"""),

        HumanMessage(content=question)
    ]
    response = llm_tool.invoke(messages)

    if response.tool_calls:

        for tool_call in response.tool_calls:

            tool_name = tool_call["name"]
            args = tool_call.get("args", {})

            if tool_name == "execute_sql":

                if "query" not in args:
                    return {
                        "type": "error",
                        "error": f"Missing query argument: {args}"}

                return execute_sql.invoke(
                    {
                        "query": args["query"]
                    }
                )

            elif tool_name == "generate_visualization":

                if "query" not in args:

                    return {
                        "type": "error",
                        "error": f"Missing query argument: {args}"
                    }

                if "code" not in args:

                    return {
                        "type": "error",
                        "error": f"Missing code argument: {args}"
                    }

                return generate_visualization.invoke(
                    {
                        "query": args["query"],
                        "code": args["code"]
                    }
                )

    return {
        "type": "text",
        "answer": response.content
    }



@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    uploaded_files = []
    generated_files = []
    errors = []

    for file in files:
        if not file.filename:
            continue

        filename = os.path.basename(file.filename)

        if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
            errors.append(f"{filename}: Unsupported file type")
            continue

        try:
            contents = await file.read()

            files_created = save_uploaded_file(contents, filename)

            uploaded_files.append(filename)
            generated_files.extend(files_created)

            for generated_file in files_created:
                filepath = os.path.join(STORAGE_PATH, generated_file)

                try:
                    if not file_exist(generated_file):
                        upload_file_s3(filepath, generated_file)
                        print(f"Uploaded to S3: {generated_file}")
                    else:
                        print(f"Already exists in S3: {generated_file}")

                except Exception as s3_error:
                    errors.append(
                        f"{generated_file}: S3 upload failed: {str(s3_error)}"
                    )

        except Exception as exp:
            errors.append(f"{filename}: {str(exp)}")

    return {
        "message": "Upload completed",
        "uploaded_files": uploaded_files,
        "generated_files": generated_files,
        "errors": errors
    }


@app.post("/ask")
async def ask_question( request: QuestionRequest):
    return get_response(request.question)

app.mount(
    "/charts",
    StaticFiles(directory=CHART_PATH),
    name="charts")


@app.get("/")
async def home():

    return FileResponse(
        "static/index.html"
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000)