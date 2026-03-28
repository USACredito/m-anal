import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")
URL = f"https://n8n-nocodb.ilwtyk.easypanel.host/api/v3/data/{BASE_ID}/m1nqjj8zpadeii5/records"
print(requests.get(URL, headers={"xc-token": TOKEN}).text)
