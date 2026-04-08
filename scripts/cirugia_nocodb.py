
import os
import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://n8n-nocodb.ilwtyk.easypanel.host"
TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_PROJECT_ID")

headers = {
    "xc-token": TOKEN,
    "Content-Type": "application/json"
}

def agregar_columna(table_id, column_data):
    url = f"{URL}/api/v3/meta/tables/{table_id}/columns"
    resp = requests.post(url, headers=headers, json=column_data)
    if resp.status_code in [200, 201]:
        print(f"  + Columna '{column_data['title']}' agregada con éxito.")
    elif "already exists" in resp.text.lower() or resp.status_code == 400:
        print(f"  . Columna '{column_data['title']}' ya existía o hubo un error manejable.")
    else:
        print(f"  - Error añadiendo '{column_data['title']}': {resp.status_code} {resp.text}")

# 1. Definir qué le falta a cada tabla (basado en IDs detectados previamente)
PLAN_CIRUGIA = {
    "mb7fss7inq1ieul": [ # Llamadas Ventas
        {"column_name": "estado_procesamiento", "title": "Estado", "uidt": "SingleLineText"},
        {"column_name": "duracion", "title": "Duración", "uidt": "Number"},
        {"column_name": "id_llamada_fathom", "title": "ID Fathom", "uidt": "SingleLineText"}
    ],
    "m7xzmqfd2ui9bag": [ # Calificaciones Leads
        {"column_name": "id_llamada_fathom", "title": "ID Llamada", "uidt": "SingleLineText"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ],
    "m4g9u4crgm1q0uj": [ # Calificaciones Setters
        {"column_name": "id_fathom", "title": "ID Llamada", "uidt": "SingleLineText"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ],
    "mnk4y7kn4pg8yhn": [ # Calificaciones Closers
        {"column_name": "id_fathom", "title": "ID Llamada", "uidt": "SingleLineText"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ],
    "m1nqjj8zpadeii5": [ # Resumen Mensual
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"},
        {"column_name": "promedio_calidad_setters", "title": "Promedio Setters", "uidt": "Number"},
        {"column_name": "promedio_calidad_leads", "title": "Promedio Leads", "uidt": "Number"},
        {"column_name": "promedio_calidad_closers", "title": "Promedio Closers", "uidt": "Number"},
        {"column_name": "total_llamadas_ventas", "title": "Total Ventas", "uidt": "Number"}
    ]
}

print("Iniciando cirugía de columnas...\n")

for t_id, columnas in PLAN_CIRUGIA.items():
    print(f"Procesando tabla ID: {t_id}")
    for col in columnas:
        agregar_columna(t_id, col)
    print("-" * 30)

print("\nCirugía finalizada. Ya puedes probar el script de calificaciones.")
