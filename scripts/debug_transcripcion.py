"""
debug_transcripcion.py — Diagnóstico paso a paso
Ejecutar en la consola de Easypanel para ver exactamente dónde falla la transcripción.
"""

import os
import sys
import requests
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("DIAGNÓSTICO DE TRANSCRIPCIÓN")
print("=" * 60)

# 1. Variables de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
print(f"\n[1] GEMINI_API_KEY: {'OK (' + GEMINI_API_KEY[:8] + '...)' if GEMINI_API_KEY else 'FALTA'}")

# 2. Importar Gemini
print("\n[2] Importando google.generativeai...", end="")
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    print(" OK")
except Exception as e:
    print(f" ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# 3. Tomar la primera llamada de NocoDB
print("\n[3] Buscando llamadas en NocoDB...")
try:
    from scripts.nocodb_client import listar_registros
    registros = listar_registros("llamadas_ventas", where="(Estado,eq,pendiente)", limit=1)
    if not registros:
        registros = listar_registros("llamadas_ventas", limit=1)
    if not registros:
        print("  ERROR: No hay llamadas en NocoDB")
        sys.exit(1)
    r = registros[0]
    call_id = r.get("ID Fathom") or str(r.get("Id"))
    url_audio = r.get("URL Grabación", "")
    print(f"  Llamada: {call_id}")
    print(f"  URL audio (primeros 80 chars): {url_audio[:80]}")
except Exception as e:
    print(f"  ERROR al leer NocoDB: {e}")
    traceback.print_exc()
    sys.exit(1)

# 4. Intentar descargar el audio
print("\n[4] Probando descarga del audio...")
if not url_audio:
    print("  ERROR: No hay URL de grabación en este registro.")
    sys.exit(1)

headers = {}
if "ringcentral.com" in url_audio:
    print("  Es RingCentral — intentando obtener token...")
    try:
        from scripts.sync_ringcentral import obtener_access_token
        token = obtener_access_token()
        headers["Authorization"] = f"Bearer {token}"
        print(f"  Token OK: {token[:20]}...")
    except Exception as e:
        print(f"  ERROR al obtener token RC: {e}")
        traceback.print_exc()
        sys.exit(1)

try:
    resp = requests.get(url_audio, headers=headers, stream=True, timeout=30)
    print(f"  HTTP Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Response body: {resp.text[:500]}")
        sys.exit(1)
    
    # Guardar primeros 100KB para diagnosticar
    tmp_path = "/app/.tmp/test_audio_debug.mp3"
    os.makedirs("/app/.tmp", exist_ok=True)
    with open(tmp_path, 'wb') as f:
        for i, chunk in enumerate(resp.iter_content(8192)):
            f.write(chunk)
            if i > 12:  # ~100KB
                break
    size = os.path.getsize(tmp_path)
    print(f"  Audio descargado (parcial): {size} bytes en {tmp_path}")
except Exception as e:
    print(f"  ERROR al descargar: {e}")
    traceback.print_exc()
    sys.exit(1)

# 5. Test rápido de Gemini Files API
print("\n[5] Probando subida a Gemini Files API...")
try:
    audio_file = genai.upload_file(path=tmp_path)
    print(f"  Archivo subido OK: {audio_file.name}")
    print(f"  Estado: {audio_file.state.name}")
    
    import time
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)
    
    print(f"  Estado final: {audio_file.state.name}")
    
    if audio_file.state.name == "ACTIVE":
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(["Di 'hola' en español.", audio_file])
        print(f"  Respuesta de prueba: {response.text[:100]}")
    else:
        print("  ERROR: El archivo no quedó ACTIVE")
except Exception as e:
    print(f"  ERROR en Gemini Files API: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 60)
