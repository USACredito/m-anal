"""
cleanup_old_tables.py
Elimina las tablas viejas que ya no se usan, dejando solo las v3.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://n8n-nocodb.ilwtyk.easypanel.host"
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")

headers = {"xc-token": TOKEN, "Content-Type": "application/json"}

# IDs de las tablas VIEJAS a eliminar (sin prefijo v3_)
TABLAS_A_ELIMINAR = {
    "Llamadas Ventas":          "mb7fss7inq1ieul",
    "Agentes":                  "mabd7x8ql6q6rxj",
    "Resumen Mensual":          "m1nqjj8zpadeii5",
    "Calificaciones Leads":     "m7xzmqfd2ui9bag",
    "Calificaciones Closers":   "mnk4y7kn4pg8yhn",
    "Calificaciones Setters":   "m4g9u4crgm1q0uj",
}

print("⚠️  Eliminando tablas viejas...\n")
for nombre, tid in TABLAS_A_ELIMINAR.items():
    # Intentamos con v1 y v2 ya que v3 da 404 para meta
    for api_ver in ["v1", "v2"]:
        url = f"{URL}/api/{api_ver}/db/meta/projects/{BASE_ID}/tables/{tid}"
        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"  ✅ Eliminada: {nombre} ({tid})")
            break
        elif resp.status_code == 404:
            url2 = f"{URL}/api/{api_ver}/meta/tables/{tid}"
            resp2 = requests.delete(url2, headers=headers, timeout=10)
            if resp2.status_code == 200:
                print(f"  ✅ Eliminada: {nombre} ({tid})")
                break
    else:
        print(f"  ⚠️  No se pudo eliminar {nombre} ({tid}) — puede que ya no exista o requiera eliminarla manualmente en UI.")

print("\nLimpieza finalizada.")
