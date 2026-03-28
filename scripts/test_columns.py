import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
TABLE_ID = "mb7fss7inq1ieul"
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/data/{BASE_ID}/{TABLE_ID}/records"

headers = {"xc-token": TOKEN}

resp = requests.get(URL, headers=headers)
if resp.status_code == 200:
    data = resp.json().get('list', [])
    if data:
        print(json.dumps(data[0], indent=2))
    else:
        print("La tabla está vacía. No puedo ver los nombres exactos de las columnas en respuesta vacía en NocoDB v3.")
else:
    print(resp.status_code, resp.text)
