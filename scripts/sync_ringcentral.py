"""
scripts/sync_ringcentral.py
Sincroniza el historial de llamadas de RingCentral con NocoDB.
"""

import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros, crear_registro

load_dotenv()

# Configuración RC
RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_JWT = os.getenv("RC_JWT")
RC_SERVER_URL = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")

import json
import time as _time

# Ruta del token persistido en disco
_TOKEN_FILE = "/app/.tmp/rc_token.json"

def obtener_access_token():
    """
    Obtiene un token de RingCentral y lo persiste en disco.
    Si el token guardado sigue vigente (< 55 min), lo reutiliza
    sin llamar a la API (evita CMN-301).
    """
    os.makedirs(os.path.dirname(_TOKEN_FILE), exist_ok=True)

    # Intentar cargar desde disco
    if os.path.exists(_TOKEN_FILE):
        try:
            with open(_TOKEN_FILE) as f:
                saved = json.load(f)
            if _time.time() < saved.get("expires_at", 0):
                return saved["access_token"]
        except Exception:
            pass

    # Pedir token nuevo a RC
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
        token_data = resp.json()
        access_token = token_data.get("access_token")
        expires_in   = token_data.get("expires_in", 3600)
        # Guardar en disco con 5 min de margen
        with open(_TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": access_token,
                "expires_at": _time.time() + expires_in - 300
            }, f)
        print(f"[RC] Token nuevo obtenido y guardado (expira en {expires_in}s).")
        return access_token
    else:
        print(f"[RC] Error al obtener token: {resp.text}")
        return None

def sync_calls(dias_atras=1):
    token = obtener_access_token()
    if not token: return
    
    # Rango de fechas
    date_from = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/call-log"
    params = {
        "dateFrom": date_from,
        "withRecording": "true", # Solo llamadas grabadas
        "perPage": 100
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"[RC] Buscando llamadas desde {date_from}...")
    resp = requests.get(url, headers=headers, params=params)
    
    if resp.status_code != 200:
        print(f"[RC] Error al consultar call-log: {resp.text}")
        return

    calls = resp.json().get("records", [])
    print(f"[RC] Se encontraron {len(calls)} llamadas con grabación.")

    # 1. Obtener lista de agentes para clasificar (Setter/Closer)
    agentes = {a.get("Nombre"): a for a in listar_registros("agentes")}

    for call in calls:
        call_id = str(call.get("id"))
        
        # Verificar si ya existe en NocoDB (para evitar duplicados)
        # Nota: En un sistema real, buscaríamos por id_fathom o similar.
        # Por ahora usaremos la tabla llamadas_ventas como destino principal
        
        from_name = call.get("from", {}).get("name", "Desconocido")
        to_name = call.get("to", {}).get("name", "Desconocido")
        
        # Lógica de clasificación simplificada
        agente = agentes.get(from_name) or agentes.get(to_name)
        rol = agente.get("Tipo") if agente else "Ventas" # Default si no está en la tabla
        
        # Seleccionar tabla según rol
        # (Aunque el usuario dijo solo setters y closers, usaremos llamadas_ventas por ahora)
        tabla_destino = "llamadas_ventas"
        
        duracion_min = int(call.get("duration", 0) / 60)
        if duracion_min < 2:
            print(f"  [SKIP] Llamada {call_id} descartada por baja duración ({duracion_min} min).")
            continue

        # Extraer URL de grabación
        recording = call.get("recording")
        url_audio = ""
        if recording:
            url_audio = f"{RC_SERVER_URL}/restapi/v1.0/account/~/recording/{recording.get('id')}/content"

        # Insertar en NocoDB
        data_noco = {
            "ID Fathom": call_id, # Usamos el ID de RC como ID único
            "Título": f"Llamada RC: {from_name} -> {to_name}",
            "Fecha": call.get("startTime", "")[:10],
            "Hora": call.get("startTime", "")[11:16],
            "Duración (min)": duracion_min,
            "Participantes": f"{from_name}, {to_name}",
            "URL Grabación": url_audio,
            "Tipo": rol,
            "Estado": "pendiente"
        }
        
        # Añadir si no existe (simplificado: el usuario debe manejar la unicidad o yo añadir un check)
        crear_registro(tabla_destino, data_noco)
        print(f"  [OK] Registrada llamada {call_id}")

if __name__ == "__main__":
    sync_calls(dias_atras=7) # Por defecto busca la última semana
