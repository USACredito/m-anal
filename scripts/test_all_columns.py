import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/meta/bases/{BASE_ID}/tables"

headers = {"xc-token": TOKEN}

resp = requests.get(URL, headers=headers)
tables = resp.json().get('list', [])

for t in tables:
    if t.get("title") in ["Llamadas Ventas", "Agentes", "Lista Emails", "Resumen Mensual"]:
        print(f"\n--- {t.get('title')} ---")
        t_id_detail = t.get("id")
        t_url = f"{URL}/{t_id_detail}"
        t_resp = requests.get(t_url, headers=headers).json()
        for f in t_resp.get("fields", []):
            print(f"- {f['title']} ({f.get('type')})")
