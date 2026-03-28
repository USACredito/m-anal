import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/meta/bases/{BASE_ID}/tables"

headers = {"xc-token": TOKEN}

resp = requests.get(URL, headers=headers)
if resp.status_code == 200:
    for t in resp.json().get('list', []):
        if t.get("id") == "mb7fss7inq1ieul":
            for c in t.get("columns", []):
                print(f"Columna: \"{c.get('title')}\", Nombre interno: \"{c.get('column_name')}\", Type: {c.get('uidt')}")
else:
    print(resp.status_code, resp.text)
