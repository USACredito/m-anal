import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
AIRCALL_ID = os.getenv("AIRCALL_ID")
AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")

from_date = int((datetime.now() - timedelta(days=7)).timestamp())
from_date_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")

url = "https://api.aircall.io/v1/calls"
params = {
    "from": from_date,
    "per_page": 50
}
print(f"[Aircall] Consultando llamadas de COMPAÑIA desde {from_date_str}...")
try:
    resp = requests.get(
        url,
        auth=HTTPBasicAuth(AIRCALL_ID, AIRCALL_TOKEN),
        params=params
    )
    print("Status:", resp.status_code)
    data = resp.json()
    calls = data.get("calls", [])
    print("Total (sin filtro grabación) en api/v1/calls:", len(calls))
    if calls:
        print("Muestra 1:", calls[0].get("recording"))
    calls_with_recording = [c for c in calls if c.get("recording")]
    print("Con grabación estricta:", len(calls_with_recording))
except Exception as e:
    import traceback
    traceback.print_exc()

