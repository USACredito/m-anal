
import os
import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://n8n-nocodb.ilwtyk.easypanel.host"
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")

headers = {"xc-token": TOKEN}

print(f"Diagnóstico profundo de tablas en {BASE_ID}...\n")

resp = requests.get(f"{URL}/api/v3/meta/bases/{BASE_ID}/tables", headers=headers)
if resp.status_code == 200:
    data = resp.json()
    # Si viene como objeto con propiedad 'list', la extraemos
    tables = data.get('list', []) if isinstance(data, dict) else data
    
    if not isinstance(tables, list):
        print("La respuesta no es una lista:", tables)
        exit(1)

    for t in tables:
        if not isinstance(t, dict): continue
        t_id = t.get('id')
        t_title = t.get('title')
        print(f"=== TABLA: {t_title} (ID: {t_id}) ===")
        
        # En v3, las columnas se obtienen de la misma base ID
        col_resp = requests.get(f"{URL}/api/v3/meta/tables/{t_id}/columns", headers=headers)
        if col_resp.status_code == 200:
            cols_data = col_resp.json()
            cols = cols_data.get('list', []) if isinstance(cols_data, dict) else cols_data
            for c in cols:
                if isinstance(c, dict):
                    print(f"  - {c.get('title')} (técnico: {c.get('column_name')})")
        else:
            print(f"  Error obteniendo columnas ({col_resp.status_code}): {col_resp.text[:100]}")
        print("-" * 30)
else:
    print(f"Error cargando tablas: {resp.status_code}")
