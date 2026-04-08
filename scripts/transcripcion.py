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
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import actualizar_registro, listar_registros

load_dotenv()

# Configuración Gemini — modelo sin sufijo "-latest" que no existe en v1beta
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.0-flash-exp"  # Disponible en v1beta

# Credenciales Aircall para renovar URLs expiradas
AIRCALL_ID    = os.getenv("AIRCALL_ID")
AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")

# Directorios
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)

TABLAS = ["llamadas_ventas", "llamadas_soporte", "llamadas_onboarding"]
BATCH_SIZE = 10   # Procesar máx 10 llamadas por ejecución para no sobrecargar APIs
DELAY_ENTRE_DESCARGAS = 2  # segundos entre descargas

# Token RC cacheado para toda la sesión (se obtiene 1 sola vez)
_rc_token_cache = None

def obtener_token_rc_cached() -> str | None:
    """Obtiene el token de RingCentral UNA SOLA VEZ por ejecución y lo guarda en caché."""
    global _rc_token_cache
    if _rc_token_cache:
        return _rc_token_cache
    try:
        from scripts.sync_ringcentral import obtener_access_token
        token = obtener_access_token()
        if token:
            _rc_token_cache = token
            print(f"  [RC] Token listo: {token[:20]}...")
        else:
            print("  [RC] No se pudo obtener token (rate limit o credenciales).")
        return _rc_token_cache
    except Exception as e:
        print(f"  [WARN] Error importando sync_ringcentral: {e}")
        return None


def renovar_url_aircall(call_id_str: str) -> str | None:
    """
    Pide a Aircall una URL de grabación fresca para el call_id dado.
    Las URLs de S3 de Aircall expiran rápido; hay que renovarlas antes de descargar.
    """
    if not AIRCALL_ID or not AIRCALL_TOKEN:
        return None
    try:
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
    - RingCentral: usa token Bearer cacheado (1 sola petición de token por sesión)
    - Aircall: renueva URL si está expirada (403/404)
    """
    print(f"  → [{call_id}] Descargando audio...")
    ruta_local = os.path.join(TMP_DIR, f"{call_id}.mp3")

    headers = {}
    es_ringcentral = "ringcentral.com" in url

    if es_ringcentral:
        token = obtener_token_rc_cached()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            print(f"  [SKIP] Sin token RC — saltando {call_id}")
            return None

    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=60)

        # Aircall URL expirada: renovar y reintentar
        if resp.status_code in (403, 404) and not es_ringcentral:
            print(f"    [WARN] URL expirada (HTTP {resp.status_code}). Renovando desde Aircall API...")
            nueva_url = renovar_url_aircall(call_id)
            if nueva_url:
                resp = requests.get(nueva_url, stream=True, timeout=60)

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


def transcribir_con_deepgram(ruta_audio: str, call_id: str) -> str | None:
    """
    Sube el audio a Deepgram API usando requests.
    Retorna la transcripción con los hablantes identificados.
    """
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    if not DEEPGRAM_API_KEY:
        print("    [ERROR] DEEPGRAM_API_KEY no encontrada en .env")
        return None

    print(f"  → [{call_id}] Transcribiendo con Deepgram (nova-2)...")
    
    # Parámetros: modelo nova-2, auto-puntuación, separación de hablantes
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true&utterances=true&language=es"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/mpeg"
    }

    try:
        with open(ruta_audio, "rb") as f:
            resp = requests.post(url, headers=headers, data=f, timeout=300)
        
        resp.raise_for_status()
        data = resp.json()
        
        utterances = data.get("results", {}).get("utterances", [])
        if not utterances:
            print("    [WARN] No se detectó conversación.")
            return "(Sin audio detectable)"
            
        transcripcion_final = ""
        for u in utterances:
            speaker = u.get("speaker", 0)
            text = u.get("transcript", "").strip()
            # Mapeo simple: Speaker 0 -> Speaker A, Speaker 1 -> Speaker B
            speaker_label = f"Speaker {chr(65 + int(speaker))}" 
            transcripcion_final += f"{speaker_label}: {text}\n"
            
        return transcripcion_final.strip()

    except Exception as e:
        print(f"  [ERROR] Error en Deepgram: {e}")
        if hasattr(e, "response") and getattr(e, "response") is not None:
            print(f"  [DETALLE] {e.response.text}")
        return None

def procesar_llamadas():
    """
    Recorre las tablas de NocoDB buscando llamadas 'pendientes' o sin estado.
    SOLO procesa llamadas desde el lunes de la semana actual en adelante.
    """
    total_procesadas = 0

    # Calcular lunes de esta semana
    hoy = datetime.now()
    lunes_semana = hoy - timedelta(days=hoy.weekday())
    fecha_corte = lunes_semana.strftime("%Y-%m-%d")
    print(f"\n📅 Solo procesando llamadas desde: {fecha_corte} (lunes de esta semana)")

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

        # Deduplicar y filtrar por fecha de esta semana
        vistos, registros_unicos = set(), []
        for r in registros:
            if r.get("Id") not in vistos:
                # Filtrar por fecha — solo esta semana en adelante
                fecha_llamada = r.get("Fecha", "") or ""
                if fecha_llamada < fecha_corte:
                    vistos.add(r.get("Id"))
                    continue  # Ignorar llamadas antiguas sin marcarlas
                registros_unicos.append(r)
                vistos.add(r.get("Id"))

        print(f"  Encontradas {len(registros_unicos)} llamadas para procesar.")

        # Limitar batch para no sobrecargar las APIs
        lote = registros_unicos[:BATCH_SIZE]
        if len(registros_unicos) > BATCH_SIZE:
            print(f"  [INFO] Procesando solo las primeras {BATCH_SIZE} de {len(registros_unicos)} (cron reintentará el resto).")

        for r in lote:
            nocodb_id = r.get("Id")
            call_id   = r.get("ID Fathom") or str(nocodb_id)
            url_audio = r.get("URL Grabación", "")
            titulo    = r.get("Título", "")

            if not url_audio or "example.com" in url_audio:
                continue

            # Descargar
            ruta_local = descargar_audio(url_audio, call_id, titulo)
            if not ruta_local:
                time.sleep(DELAY_ENTRE_DESCARGAS)
                continue

            # Transcribir
            texto = transcribir_con_deepgram(ruta_local, call_id)

            if texto:
                texto_final = texto[:30000]
                actualizar_registro(tabla, nocodb_id, {
                    "Transcripción Texto": texto_final,
                    "Estado": "transcrito",
                    "Fecha Procesamiento": datetime.now().strftime("%Y-%m-%d")
                })
                print(f"  [OK] [{call_id}] Transcripción completada ({len(texto_final)} chars).")
                total_procesadas += 1
            else:
                # Marcar como fallida para no reintentarla indefinidamente
                actualizar_registro(tabla, nocodb_id, {"Estado": "error_transcripcion"})

            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)

            time.sleep(DELAY_ENTRE_DESCARGAS)

    print(f"\n✅ Proceso de transcripción finalizado. Total: {total_procesadas}")


if __name__ == "__main__":
    procesar_llamadas()
