"""
scripts/sync_aircall.py
Sincroniza el historial de llamadas de Aircall con NocoDB.
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros, crear_registro
load_dotenv()

# Configuración Aircall
AIRCALL_ID = os.getenv("AIRCALL_ID")
AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")
BASE_URL = "https://api.aircall.io/v1"

def sync_calls():
    if not AIRCALL_ID or not AIRCALL_TOKEN:
        print("[Aircall] Error: Faltan credenciales en .env")
        return

    print("[Aircall] Consultando llamadas recientes...")
    url = f"{BASE_URL}/calls"
    auth = (AIRCALL_ID, AIRCALL_TOKEN)
    
    # Rango de 7 días
    from_date = int((datetime.now() - timedelta(days=7)).timestamp())
    params = {"from": from_date, "per_page": 50}

    try:
        resp = requests.get(url, auth=auth, params=params)
        if resp.status_code != 200:
            print(f"[Aircall] Error en API: {resp.text}")
            return
            
        calls = resp.json().get("calls", [])
        # Filtrar solo las que tienen grabación
        calls_with_recording = [c for c in calls if c.get("recording")]
        
        print(f"[Aircall] Se encontraron {len(calls_with_recording)} llamadas con grabación.")

        # Obtener agentes para clasificar
        agentes = {a.get("Nombre"): a for a in listar_registros("agentes")}

        for call in calls_with_recording:
            call_id = str(call.get("id"))
            
            user_name = call.get("user", {}).get("name", "Desconocido")
            contact_number = call.get("raw_digits", "Privado")
            
            # Clasificación básica por agente
            agente = agentes.get(user_name)
            rol = agente.get("Tipo") if agente else "Ventas"
            
            # Mapeo a tabla NocoDB
            data_noco = {
                "ID Fathom": call_id, # ID único para tracking
                "Título": f"Llamada Aircall: {user_name} -> {contact_number}",
                "Fecha": datetime.fromtimestamp(call.get("started_at", 0)).strftime("%Y-%m-%d"),
                "Hora": datetime.fromtimestamp(call.get("started_at", 0)).strftime("%H:%M"),
                "Duración (min)": int(call.get("duration", 0) / 60),
                "Participantes": f"{user_name}, {contact_number}",
                "URL Grabación": call.get("recording"),
                "Tipo": rol,
                "Estado": "pendiente"
            }
            
            # Insertar en NocoDB (Ventas por defecto)
            crear_registro("llamadas_ventas", data_noco)
            print(f"  [OK] Registrada llamada {call_id} de {user_name}")

    except Exception as e:
        print(f"[Aircall] Error inesperado: {str(e)}")

if __name__ == "__main__":
    sync_calls()
