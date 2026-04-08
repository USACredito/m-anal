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

def _get_ids_existentes() -> set:
    """Carga todos los IDs existentes en llamadas_ventas para evitar duplicados."""
    try:
        registros = listar_registros("llamadas_ventas")
        return {str(r.get("ID Fathom", "")) for r in registros if r.get("ID Fathom")}
    except Exception as e:
        print(f"[Aircall] WARN: No se pudo verificar IDs existentes: {e}")
        return set()

def sync_calls():
    if not AIRCALL_ID or not AIRCALL_TOKEN:
        print("[Aircall] Error: Faltan credenciales en .env")
        return

    print("[Aircall] Consultando llamadas recientes (últimos 8 días)...")
    url = f"{BASE_URL}/calls"
    auth = (AIRCALL_ID, AIRCALL_TOKEN)

    # Rango de 8 días
    from_date = int((datetime.now() - timedelta(days=8)).timestamp())
    params = {"from": from_date, "per_page": 100}

    try:
        resp = requests.get(url, auth=auth, params=params)
        if resp.status_code != 200:
            print(f"[Aircall] Error en API: {resp.text}")
            return

        calls = resp.json().get("calls", [])
        calls_with_recording = [c for c in calls if c.get("recording")]

        print(f"[Aircall] Se encontraron {len(calls_with_recording)} llamadas con grabación.")

        # Cargar IDs existentes para deduplicación
        ids_existentes = _get_ids_existentes()
        print(f"[Aircall] IDs ya en NocoDB: {len(ids_existentes)}")

        # Obtener agentes para clasificar
        agentes = {a.get("Nombre"): a for a in listar_registros("agentes")}

        nuevas = 0
        for call in calls_with_recording:
            call_id = str(call.get("id"))

            # Deduplicación
            if call_id in ids_existentes:
                continue

            user_name = call.get("user", {}).get("name", "Desconocido")
            contact_number = call.get("raw_digits", "Privado")

            duracion_min = int(call.get("duration", 0) / 60)
            if duracion_min < 2:
                print(f"  [SKIP] Llamada {call_id} descartada por baja duración ({duracion_min} min).")
                continue

            # Clasificar setter/closer
            agente = agentes.get(user_name)
            rol = agente.get("Tipo", "ventas").lower() if agente else "ventas"
            if "setter" in rol:
                tipo_llamada = "setter"
            elif "closer" in rol:
                tipo_llamada = "closer"
            else:
                tipo_llamada = "ventas"

            data_noco = {
                "ID Fathom": call_id,
                "Título": f"Llamada Aircall: {user_name} -> {contact_number}",
                "Fecha": datetime.fromtimestamp(call.get("started_at", 0)).strftime("%Y-%m-%d"),
                "Hora": datetime.fromtimestamp(call.get("started_at", 0)).strftime("%H:%M"),
                "Duración (min)": duracion_min,
                "Participantes": f"{user_name}, {contact_number}",
                "URL Grabación": call.get("recording"),
                "Tipo": tipo_llamada,
                "Estado": "pendiente"
            }

            crear_registro("llamadas_ventas", data_noco)
            ids_existentes.add(call_id)
            nuevas += 1
            print(f"  [OK] Nueva llamada {call_id} ({tipo_llamada})")

        print(f"[Aircall] Sync completado: {nuevas} nuevas llamadas insertadas.")

    except Exception as e:
        print(f"[Aircall] Error inesperado: {str(e)}")

if __name__ == "__main__":
    sync_calls()
