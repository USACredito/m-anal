import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
TABLE_ID = "m1nqjj8zpadeii5"
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/data/{BASE_ID}/{TABLE_ID}/records"

headers = {"xc-token": TOKEN, "Content-Type": "application/json"}
payload = {
    "Mes-Año": "2026-03",
    "Promedio Leads": 0,
    "Promedio Closers": 0,
    "Promedio Onboarding": 0,
    "Total Ventas": 0,
    "Total Soporte": 0,
    "Total Onboarding": 0
}

resp = requests.post(URL, headers=headers, json=payload)
print(resp.status_code, resp.text)
