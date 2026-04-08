"""
scripts/transcripcion.py — VERSIÓN UNIFICADA (GEMINI)
Procesa llamadas pendientes en NocoDB.
Descarga audio y lo transcribe usando Gemini.
FIX: Renueva URLs expiradas de Aircall. Usa modelo Gemini correcto.
"""

import os
import sys
import requests
import time
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import actualizar_registro, listar_registros

load_dotenv()

# Configuración Gemini — modelo sin sufijo "-latest" que no existe en v1beta
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"   # <-- CORREGIDO: sin "-latest"

# Credenciales Aircall para renovar URLs expiradas
AIRCALL_ID    = os.getenv("AIRCALL_ID")
AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")

# Directorios
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)

TABLAS = ["llamadas_ventas", "llamadas_soporte", "llamadas_onboarding"]


def renovar_url_aircall(call_id_str: str) -> str | None:
    """
    Pide a Aircall una URL de grabación fresca para el call_id dado.
    Las URLs de S3 de Aircall expiran rápido; hay que renovarlas antes de descargar.
    """
    if not AIRCALL_ID or not AIRCALL_TOKEN:
        return None
    try:
        # El call_id puede venir como "3647174148" o con prefijo; limpiamos
        numeric_id = ''.join(filter(str.isdigit, call_id_str.split("-")[0] if "-" in call_id_str else call_id_str))
        if not numeric_id:
            return None
        url = f"https://api.aircall.io/v1/calls/{numeric_id}"
        resp = requests.get(url, auth=(AIRCALL_ID, AIRCALL_TOKEN), timeout=15)
        if resp.status_code == 200:
            fresh_url = resp.json().get("call", {}).get("recording")
            if fresh_url:
                print(f"    [Aircall] URL renovada OK para {numeric_id}")
                return fresh_url
    except Exception as e:
        print(f"    [WARN] No se pudo renovar URL Aircall: {e}")
    return None


def descargar_audio(url: str, call_id: str, titulo: str = ""):
    """
    Descarga un archivo de audio desde una URL y lo guarda en .tmp/
    Si la URL de Aircall está expirada (403/404), renueva automáticamente.
    """
    print(f"  → [{call_id}] Descargando audio...")
    ruta_local = os.path.join(TMP_DIR, f"{call_id}.mp3")

    headers = {}
    if "ringcentral.com" in url or "platform.devtest.ringcentral.com" in url:
        try:
            from scripts.sync_ringcentral import obtener_access_token
            token = obtener_access_token()
            headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            print(f"    [WARN] No se pudo obtener token RC: {e}")

    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=60)

        # Si Aircall devuelve error de URL expirada, renovar y reintentar
        if resp.status_code in (403, 404) and ("s3.amazonaws.com" in url or "aircall" in url.lower()):
            print(f"    [WARN] URL expirada (HTTP {resp.status_code}). Renovando desde Aircall API...")
            nueva_url = renovar_url_aircall(call_id)
            if nueva_url:
                resp = requests.get(nueva_url, stream=True, timeout=60)
                url = nueva_url  # actualizar para el log

        resp.raise_for_status()

        with open(ruta_local, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = os.path.getsize(ruta_local) // 1024
        print(f"    [OK] Descargado: {size_kb} KB")
        return ruta_local

    except Exception as e:
        print(f"  [ERROR] No se pudo descargar audio: {e}")
        return None


def transcribir_con_gemini(ruta_audio: str, call_id: str) -> str | None:
    """
    Sube el audio a Gemini y obtiene la transcripción.
    """
    print(f"  → [{call_id}] Transcribiendo con Gemini {MODEL_NAME}...")
    try:
        audio_file = genai.upload_file(path=ruta_audio)

        # Esperar procesamiento
        max_wait = 60
        waited = 0
        while audio_file.state.name == "PROCESSING" and waited < max_wait:
            time.sleep(3)
            waited += 3
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name != "ACTIVE":
            print(f"    [WARN] Archivo Gemini en estado: {audio_file.state.name}")
            return None

        model = genai.GenerativeModel(MODEL_NAME)
        prompt = (
            "Eres un transcriptor experto. Transcribe este audio de llamada de ventas. "
            "Identifica a los hablantes (Speaker A / Speaker B) y mantén el idioma original (Español). "
            "Formato: 'Speaker A: [texto]\\nSpeaker B: [texto]'"
        )
        response = model.generate_content([prompt, audio_file])
        return response.text

    except Exception as e:
        print(f"  [ERROR] Error en Gemini: {e}")
        return None


def procesar_llamadas():
    """
    Recorre las tablas de NocoDB buscando llamadas 'pendientes' o sin estado.
    """
    total_procesadas = 0

    for tabla in TABLAS:
        print(f"\n--- Revisando tabla: {tabla} ---")
        try:
            registros_pendientes  = listar_registros(tabla, where="(Estado,eq,pendiente)")
            registros_vacios      = listar_registros(tabla, where="(Estado,is,null)")
            registros_vacios_str  = listar_registros(tabla, where="(Estado,eq,)")
            registros = registros_pendientes + registros_vacios + registros_vacios_str
        except Exception as e:
            print(f"  [WARN] Error listando registros: {e}")
            continue

        # Deduplicar
        vistos, registros_unicos = set(), []
        for r in registros:
            if r.get("Id") not in vistos:
                registros_unicos.append(r)
                vistos.add(r.get("Id"))

        print(f"  Encontradas {len(registros_unicos)} llamadas para procesar.")

        for r in registros_unicos:
            nocodb_id = r.get("Id")
            call_id   = r.get("ID Fathom") or str(nocodb_id)
            url_audio = r.get("URL Grabación", "")
            titulo    = r.get("Título", "")

            if not url_audio or "example.com" in url_audio:
                continue

            # Descargar
            ruta_local = descargar_audio(url_audio, call_id, titulo)
            if not ruta_local:
                continue

            # Transcribir
            texto = transcribir_con_gemini(ruta_local, call_id)

            if texto:
                texto_final = texto[:30000]
                actualizar_registro(tabla, nocodb_id, {
                    "Transcripción Texto": texto_final,
                    "Estado": "transcrito",
                    "Fecha Procesamiento": datetime.now().strftime("%Y-%m-%d")
                })
                print(f"  [OK] [{call_id}] Transcripción completada ({len(texto_final)} chars).")
                total_procesadas += 1

            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)

    print(f"\n✅ Proceso de transcripción finalizado. Total: {total_procesadas}")


if __name__ == "__main__":
    procesar_llamadas()
