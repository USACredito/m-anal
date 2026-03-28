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

# La base de la API suele ser /api/v1
NOCODB_BASE_API_URL = f"{RAW_URL}/api/v1"

HEADERS = {
    "xc-token": NOCODB_API_TOKEN,
    "Content-Type": "application/json",
}


def _get_table_url(table_name: str) -> str:
    """Construye la URL para una tabla de NocoDB siguiendo el formato v1."""
    return f"{NOCODB_BASE_API_URL}/db/data/noco/{PROJECT_ID}/{table_name}"


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

        records = data.get("list", [])
        all_records.extend(records)

        page_info = data.get("pageInfo", {})
        total = page_info.get("totalRows", len(all_records))

        if offset + limit >= total:
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
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
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
    url = f"{_get_table_url(table_name)}/{record_id}"
    resp = requests.patch(url, headers=HEADERS, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def obtener_registro(table_name: str, record_id: int) -> dict:
    """Obtiene un registro por su ID."""
    url = f"{_get_table_url(table_name)}/{record_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()
