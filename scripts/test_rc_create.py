import sys
sys.path.append(".")
import os
import requests
from dotenv import load_dotenv
from scripts.nocodb_client import _get_table_url, HEADERS

load_dotenv()
url = _get_table_url("llamadas_ventas")
data_noco = {
    "ID Fathom": "123456",
    "Título": "Llamada RC: A -> B",
    "Fecha": "2026-03-30",
    "Hora": "10:00",
    "Duración (min)": 5,    # int test!
    "Participantes": "A, B",
    "URL Grabación": "http://example.com/audio.mp3",
    "Tipo": "Ventas",
    "Estado": "pendiente"
}
resp = requests.post(url, headers=HEADERS, json={"fields": data_noco})
print(resp.status_code, resp.text)
