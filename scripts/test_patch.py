import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/data/{BASE_ID}/m1nqjj8zpadeii5/records"

# Test PATCH
payload = {
    "Id": 1,
    "Mes-Año": "2026-03-PATCHED"
}
# Will this fail like POST?
print("PATCH normal:", requests.patch(URL, headers={"xc-token": TOKEN, "Content-Type": "application/json"}, json=payload).text)

payload_fields = {
    "id": 1,
    "fields": {"Mes-Año": "2026-03-PATCHED2"}
}
print("PATCH fields:", requests.patch(URL, headers={"xc-token": TOKEN, "Content-Type": "application/json"}, json=payload_fields).text)

