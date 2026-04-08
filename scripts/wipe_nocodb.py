
import os
import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://n8n-nocodb.ilwtyk.easypanel.host"
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")

headers = {"xc-token": TOKEN}

# Tablas a eliminar para resetear el sistema
TABLAS_A_LIMPIAR = [
    "llamadas_ventas",
    "calificaciones_leads",
    "calificaciones_closers",
    "calificaciones_setters",
    "resumen_mensual_calidad"
]

print(f"Iniciando limpieza de {BASE_ID}...\n")

# 1. Obtener los IDs actuales de las tablas
resp = requests.get(f"{URL}/api/v3/meta/bases/{BASE_ID}/tables", headers=headers)
if resp.status_code == 200:
    data = resp.json()
    tables = data.get('list', []) if isinstance(data, dict) else data
    
    for t in tables:
        t_id = t.get('id')
        t_title = t.get('title')
        # Buscamos si el Titulo o el ID coinciden con lo que queremos limpiar
        clean = False
        for target in TABLAS_A_LIMPIAR:
             if target.lower() in t_title.lower().replace(" ", "_") or target == t_id:
                 clean = True
                 break
        
        if clean:
            print(f"Eliminando tabla: {t_title} ({t_id})...")
            del_resp = requests.delete(f"{URL}/api/v3/meta/tables/{t_id}", headers=headers)
            if del_resp.status_code == 200:
                print("  - Eliminada con éxito.")
            else:
                print(f"  - Error eliminando: {del_resp.status_code} {del_resp.text}")
else:
    print(f"Error al listar tablas: {resp.status_code}")

print("\nLimpieza finalizada.")
