## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the required dependencies using `requirements.txt`.
4. Add the required API and storage credentials to the `.env` file.
5. Start the FastAPI development server:

```bash
python -m fastapi dev app.py
```

The application will run locally on `http://127.0.0.1:8000`.

## Tech Stack

* **Python** – Main programming language.
* **FastAPI** – Backend API and web server.
* **Google Gemini** – Natural-language understanding and SQL generation.
* **LangChain** – Connects the application with the Gemini model and tools.
* **DuckDB** – Query engine for analyzing CSV data.
* **Pandas** – Data cleaning and processing.
* **Matplotlib & Seaborn** – Data visualization.
* **Boto3** – Uploading and managing files in S3-compatible storage.
* **Uvicorn** – Runs the FastAPI application.

## Project Structure

```text
AI-Powered-DataAnalysis/
│
├── app.py
├── database.py
├── s3_storage.py
│
├── static/
│   └── index.html
│
├── storage/
│   └── uploaded CSV files
│
├── .env
├── requirements.txt
└── README.md
```


## DemoLink
```bash
https://www.awesomescreenshot.com/video/56693048?key=9ed3717adc8071fa4dd21ced3ee1d2b4
```

## Document Link 
```bash
https://docs.google.com/document/d/1hv3EhqBI827P_lxeTMwf0GbXXsl6n4icTJLw_eIQFbc/edit?usp=sharing
```
