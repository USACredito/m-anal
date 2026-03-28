"""
scripts/transcripcion.py — VERSIÓN UNIFICADA (GEMINI)
Procesa llamadas pendientes en NocoDB.
Descarga audio de RingCentral/Aircall/Fathom y lo transcribe usando Gemini 1.5 Flash.
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

# Configuración Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

# Directorios
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)

TABLAS = ["llamadas_ventas", "llamadas_soporte", "llamadas_onboarding"]

def descargar_audio(url, call_id):
    """
    Descarga un archivo de audio desde una URL y lo guarda en .tmp/
    """
    print(f"  → [{call_id}] Descargando audio...")
    ruta_local = os.path.join(TMP_DIR, f"{call_id}.mp3")
    
    # Manejo de headers para RingCentral (si es necesario)
    headers = {}
    if "ringcentral.com" in url:
        from scripts.sync_ringcentral import obtener_access_token
        token = obtener_access_token()
        headers["Authorization"] = f"Bearer {token}"
    elif "aircall.io" in url:
        # Aircall usa Basic Auth si es necesario, pero las recording URLs suelen ser públicas/firmadas
        pass

    try:
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()
        with open(ruta_local, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return ruta_local
    except Exception as e:
        print(f"  [ERROR] No se pudo descargar audio: {e}")
        return None

def transcribir_con_gemini(ruta_audio, call_id):
    """
    Sube el audio a Gemini y obtiene la transcripción.
    """
    print(f"  → [{call_id}] Transcribiendo con Gemini 1.5 Flash...")
    try:
        # 1. Subir archivo
        audio_file = genai.upload_file(path=ruta_audio)
        
        # 2. Esperar procesamiento
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)
            
        if audio_file.state.name == "FAILED":
            return None

        # 3. Generar contenido
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = (
            "Eres un transcriptor experto. Transcribe este audio de llamada de ventas. "
            "Identifica a los hablantes (Speaker A/B) y mantén el idioma original (Español)."
        )
        response = model.generate_content([prompt, audio_file])
        
        # Opcional: Limpiar archivo en la nube
        # genai.delete_file(audio_file.name)
        
        return response.text
    except Exception as e:
        print(f"  [ERROR] Error en Gemini: {e}")
        return None

def procesar_llamadas():
    """
    Recorre las tablas de NocoDB buscando llamadas 'pendientes'.
    """
    total_procesadas = 0
    
    for tabla in TABLAS:
        print(f"\n--- Revisando tabla: {tabla} ---")
        registros = listar_registros(tabla, where="(estado_procesamiento,eq,pendiente)")
        
        for r in registros:
            nocodb_id = r.get("Id")
            call_id = r.get("id_fathom") or str(nocodb_id)
            url_audio = r.get("url_grabacion")
            
            if not url_audio:
                print(f"  → [{call_id}] Sin URL de grabación. Saltando.")
                continue

            # 1. Descargar
            ruta_local = descargar_audio(url_audio, call_id)
            if not ruta_local: continue
            
            # 2. Transcribir
            texto = transcribir_con_gemini(ruta_local, call_id)
            
            if texto:
                # 3. Actualizar NocoDB
                actualizar_registro(tabla, nocodb_id, {
                    "transcripcion_texto": texto,
                    "estado_procesamiento": "transcrito",
                    "fecha_procesamiento": datetime.now().strftime("%Y-%m-%d")
                })
                print(f"  [OK] [{call_id}] Transcripción completada.")
                total_procesadas += 1
            
            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)

    print(f"\n✅ Proceso de transcripción finalizado. Total: {total_procesadas}")

if __name__ == "__main__":
    procesar_llamadas()
