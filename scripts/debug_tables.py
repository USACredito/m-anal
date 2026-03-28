import os
import requests
from dotenv import load_dotenv

load_dotenv()

FULL_URL = os.getenv("NOCODB_URL", "")
API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")
PROJECT_ID = "p9sqt7wk1bkr0lq"
if "/nc/" in FULL_URL:
    PROJECT_ID = FULL_URL.split("/nc/")[-1].split("/")[0]

BASE_API_URL = FULL_URL.split("/dashboard")[0] + "/api/v1"
HEADERS = {"xc-token": API_TOKEN}

def main():
    url = f"{BASE_API_URL}/db/meta/projects/{PROJECT_ID}/tables"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        tables = resp.json()
        print("TABLAS ENCONTRADAS:")
        for t in tables.get("list", []):
            print(f"- {t.get('table_name')} (ID: {t.get('id')}, Title: {t.get('title')})")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    main()
