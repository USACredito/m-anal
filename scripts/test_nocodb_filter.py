import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
# "llamadas_ventas": "mb7fss7inq1ieul"
TABLE_ID = "mb7fss7inq1ieul"
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/data/{BASE_ID}/{TABLE_ID}/records"

headers = {"xc-token": TOKEN}

# Test no filter
resp = requests.get(URL, headers=headers)
print(f"No filter: {resp.status_code}")

# Test simple filter
resp = requests.get(URL, headers=headers, params={"where": "(estado_procesamiento,eq,pendiente)"})
print(f"Filter 1: {resp.status_code} - {resp.text[:100]}")

# Test filter with quotes
resp = requests.get(URL, headers=headers, params={"where": "(estado_procesamiento,eq,'pendiente')"})
print(f"Filter 2: {resp.status_code} - {resp.text[:100]}")

