import sys
sys.path.append(".")
import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_JWT = os.getenv("RC_JWT")
RC_SERVER_URL = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")

def obtener_access_token():
    url = f"{RC_SERVER_URL}/restapi/oauth/token"
    auth_header = base64.b64encode(f"{RC_CLIENT_ID}:{RC_CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": RC_JWT
    }
    resp = requests.post(url, headers=headers, data=data)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

token = obtener_access_token()
if token:
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/call-log"
    params = {
        "dateFrom": date_from,
        "withRecording": "true",
        "perPage": 10
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"[RC] Buscando COMPANY LLAMADAS desde {date_from}...")
    resp = requests.get(url, headers=headers, params=params)
    print("Status:", resp.status_code)
    try:
        data = resp.json()
        print("Total company calls:", len(data.get("records", [])))
        if data.get("records"):
            print("Primer record ID:", data["records"][0].get('id'))
    except e:
        print(resp.text)
