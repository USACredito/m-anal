"""
scripts/migrate_add_resumen_fields.py
Agrega los campos Puntos Fuertes, Áreas de Mejora y Resumen
a las tablas calificaciones_setters y calificaciones_closers en NocoDB.

Ejecutar UNA sola vez:
    python scripts/migrate_add_resumen_fields.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

RAW_URL = os.getenv("NOCODB_URL", "").split("/dashboard")[0].rstrip("/")
TOKEN   = os.getenv("NOCODB_API_TOKEN", "")

HEADERS = {
    "xc-token": TOKEN,
    "Content-Type": "application/json",
}

# Table IDs (de nocodb_client.py)
TABLAS = {
    "calificaciones_setters": "mgv0z5ydz1vpbfq",
    "calificaciones_closers": "muhe0x1pdjx5rs3",
}

# Campos a agregar
NUEVOS_CAMPOS = [
    {"title": "Puntos Fuertes", "uidt": "LongText"},
    {"title": "Áreas de Mejora", "uidt": "LongText"},
    {"title": "Resumen",         "uidt": "LongText"},
]


def campo_ya_existe(table_id: str, titulo: str) -> bool:
    """Verifica si una columna con ese titulo ya existe en la tabla."""
    url = f"{RAW_URL}/api/v1/db/meta/tables/{table_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        columnas = resp.json().get("columns", [])
        for col in columnas:
            if col.get("title", "").lower() == titulo.lower():
                return True
    return False

def agregar_campo(table_id: str, tabla_nombre: str, campo: dict):
    titulo = campo["title"]
    if campo_ya_existe(table_id, titulo):
        print(f"  [--] [{tabla_nombre}] '{titulo}' ya existia, omitiendo.")
        return
    url = f"{RAW_URL}/api/v1/db/meta/tables/{table_id}/columns"
    resp = requests.post(url, headers=HEADERS, json=campo, timeout=15)
    if resp.status_code in (200, 201):
        print(f"  [OK] [{tabla_nombre}] Campo '{titulo}' creado.")
    else:
        print(f"  [ERR] [{tabla_nombre}] '{titulo}': HTTP {resp.status_code} -> {resp.text[:300]}")


def main():
    print("=== Migración: agregar campos de resumen a NocoDB ===\n")

    for nombre, table_id in TABLAS.items():
        print(f"Tabla: {nombre} ({table_id})")
        for campo in NUEVOS_CAMPOS:
            agregar_campo(table_id, nombre, campo)
        print()

    print("Migración completada.")
    print("Ahora el agente de calificaciones guardará Puntos Fuertes, Áreas de Mejora y Resumen.")
    print("El dashboard los mostrará en el modal de detalle de cada llamada.")


if __name__ == "__main__":
    main()
