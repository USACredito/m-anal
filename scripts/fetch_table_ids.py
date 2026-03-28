import os
import requests
from dotenv import load_dotenv

load_dotenv()

# We need to hit the external URL from the laptop
URL = "https://n8n-nocodb.ilwtyk.easypanel.host"
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")

headers = {"xc-token": TOKEN}

print(f"Buscando tablas en {BASE_ID}...")
# Try v3 meta api
endpoints = [
    f"{URL}/api/v3/meta/bases/{BASE_ID}/tables",
    f"{URL}/api/v2/meta/bases/{BASE_ID}/tables",
    f"{URL}/api/v1/meta/bases/{BASE_ID}/tables",
]

for endpoint in endpoints:
    print(f"Probando {endpoint}...")
    resp = requests.get(endpoint, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        tables = data.get("list", []) or data
        if isinstance(tables, list):
            for t in tables:
                print(f"Tabla: {t.get('title')} -> ID: {t.get('id')}")
        else:
            print("Formato no esperado:", tables)
        break
    else:
        print(f"Falla ({resp.status_code}): {resp.text[:100]}")
