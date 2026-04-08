"""
nocodb_client.py
Cliente compartido para interactuar con la API de NocoDB.
Todas las operaciones CRUD están centralizadas aquí.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuración desde .env
RAW_URL = os.getenv("NOCODB_URL", "").split("/dashboard")[0].rstrip("/")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")
PROJECT_ID = os.getenv("NOCODB_PROJECT_ID", "p9sqt7wk1bkr0lq")

MAPA_TABLAS = {
    # Usamos los nombres reales de las tablas para que la API las resuelva dinámicamente
    "llamadas_ventas": "llamadas_ventas",
    "agentes": "agentes",
    "calificaciones_leads": "calificaciones_leads",
    "calificaciones_closers": "calificaciones_closers",
    "calificaciones_setters": "calificaciones_setters",
    "resumen_mensual_calidad": "resumen_mensual_calidad"
}

NOCODB_BASE_API_URL = f"{RAW_URL}/api/v3"

HEADERS = {
    "xc-token": NOCODB_API_TOKEN,
    "Content-Type": "application/json",
}

def _get_table_url(table_name: str) -> str:
    """Construye la URL para una tabla de NocoDB v3 usando su Table ID."""
    table_id = MAPA_TABLAS.get(table_name, table_name)
    return f"{NOCODB_BASE_API_URL}/data/{PROJECT_ID}/{table_id}/records"

def listar_registros(table_name: str, where: str = "", limit: int = 200) -> list:
    """
    Obtiene todos los registros de una tabla con paginación automática.
    :param table_name: Nombre de la tabla en NocoDB
    :param where: Filtro en formato NocoDB (ej: '(estado_procesamiento,eq,pendiente)')
    :param limit: Registros por página (máx 200 recomendado)
    :return: Lista de registros
    """
    url = _get_table_url(table_name)
    all_records = []
    offset = 0

    while True:
        params = {"limit": limit, "offset": offset}
        if where:
            params["where"] = where

        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        raw_list = data.get("records", [])
        for r in raw_list:
            if "fields" in r:
                flat = r["fields"].copy()
                flat["Id"] = r.get("id")
                all_records.append(flat)
            else:
                all_records.append(r)

        if len(raw_list) < limit:
            break
        offset += limit

    return all_records


def crear_registro(table_name: str, payload: dict) -> dict:
    """
    Crea un nuevo registro en la tabla especificada.
    :param table_name: Nombre de la tabla
    :param payload: Datos del registro
    :return: Registro creado
    """
    url = _get_table_url(table_name)
    # En v3 se envuelve en {"fields": {...}}
    wrapped_payload = {"fields": payload}
    resp = requests.post(url, headers=HEADERS, json=wrapped_payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def actualizar_registro(table_name: str, record_id: int, payload: dict) -> dict:
    """
    Actualiza un registro existente por su ID interno de NocoDB.
    :param table_name: Nombre de la tabla
    :param record_id: ID del registro en NocoDB
    :param payload: Campos a actualizar
    :return: Respuesta de la API
    """
    url = _get_table_url(table_name)
    # En v3, el PATCH requiere {"id": X, "fields": {...}}
    wrapped_payload = {"id": record_id, "fields": payload}
    resp = requests.patch(url, headers=HEADERS, json=wrapped_payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def obtener_registro(table_name: str, record_id: int) -> dict:
    """Obtiene un registro por su ID."""
    url = f"{_get_table_url(table_name)}/{record_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()
