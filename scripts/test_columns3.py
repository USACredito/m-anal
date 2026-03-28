import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
TABLE_ID = "mb7fss7inq1ieul"
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/meta/bases/{BASE_ID}/tables/{TABLE_ID}"

headers = {"xc-token": TOKEN}

resp = requests.get(URL, headers=headers)
print("Data:", resp.text[:1500])
