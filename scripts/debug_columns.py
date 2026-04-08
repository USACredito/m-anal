
import os
import requests
from dotenv import load_dotenv

load_dotenv()
RAW_URL = os.getenv("NOCODB_URL", "").split("/dashboard")[0].rstrip("/")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")
PROJECT_ID = os.getenv("NOCODB_PROJECT_ID", "p9sqt7wk1bkr0lq")

headers = {"xc-token": NOCODB_API_TOKEN}
table_id = "mb7fss7inq1ieul" # ID de Llamadas Ventas segun el log anterior

url = f"{RAW_URL}/api/v3/meta/tables/{table_id}"
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    columns = resp.json().get("columns", [])
    print(f"\nColumnas en Llamadas Ventas ({table_id}):")
    for col in columns:
        print(f" - {col['title']} (tecnico: {col['column_name']})")
else:
    print(f"Error al obtener columnas: {resp.status_code} - {resp.text}")
