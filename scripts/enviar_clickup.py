"""
enviar_clickup.py — Nueva Integración
Lee los análisis semanales directamente desde la carpeta .tmp/ generada
por analisis_gemini.py y los crea como Tareas en ClickUp.

Porciones que antes iban por email en reportes PDF ahora van a la Lista de ClickUp.
"""

import argparse
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN", "")
CLICKUP_LIST_ID = "901109287295"  # Obtenido del backup de N8N
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")

def crear_tarea_clickup(titulo, contenido):
    if not CLICKUP_API_TOKEN:
        print("[CLICKUP] ERROR: No se encontró CLICKUP_API_TOKEN en el archivo .env. Ignorando envío.")
        return False
    
    url = f"https://api.clickup.com/api/v2/list/{CLICKUP_LIST_ID}/task"
    
    headers = {
        "Authorization": CLICKUP_API_TOKEN,
        "Content-Type": "application/json"
    }

    # ClickUp limits description length, so let's truncate if it's absurdly massive (e.g., > 8000)
    if len(contenido) > 8000:
        contenido = contenido[:8000] + "\n\n...[mensaje truncado por longitud máxima]..."

    payload = {
        "name": titulo,
        "description": contenido,
        "status": "TO DO"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            print(f"[CLICKUP] ✅ Reporte '{titulo}' creado exitosamente como tarea.")
            return True
        else:
            print(f"[CLICKUP] ❌ Error creando tarea: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[CLICKUP] ❌ Error de conexión: {e}")
        return False

def enviar_reportes(inicio, fin):
    print(f"\n[CLICKUP] Preparando creación de tareas de análisis. Periodo: {inicio} a {fin}")

    archivos_ventas = [
        f"reporte_errores_ventas_{inicio}_{fin}.txt", 
        f"reporte_marketing_{inicio}_{fin}.txt"
    ]
    archivo_soporte = f"reporte_soporte_{inicio}_{fin}.txt"
    archivo_onboarding = f"reporte_onboarding_{inicio}_{fin}.txt"

    # Enviar reporte Ventas
    for nombre_arc in archivos_ventas:
        ruta = os.path.join(TMP_DIR, nombre_arc)
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                texto = f.read()
            titulo = f"📊 Análisis de Ventas/Marketing: {inicio} → {fin} ({nombre_arc.split('_')[1]})"
            crear_tarea_clickup(titulo, texto)

    # Enviar reporte Soporte
    ruta_soporte = os.path.join(TMP_DIR, archivo_soporte)
    if os.path.exists(ruta_soporte):
        with open(ruta_soporte, "r", encoding="utf-8") as f:
            texto = f.read()
        titulo = f"🎧 Análisis de Soporte: {inicio} → {fin}"
        crear_tarea_clickup(titulo, texto)

    # Enviar reporte Onboarding
    ruta_onboarding = os.path.join(TMP_DIR, archivo_onboarding)
    if os.path.exists(ruta_onboarding):
        with open(ruta_onboarding, "r", encoding="utf-8") as f:
            texto = f.read()
        titulo = f"🚀 Análisis de Onboarding: {inicio} → {fin}"
        crear_tarea_clickup(titulo, texto)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fin", required=True)
    args = parser.parse_args()

    enviar_reportes(args.inicio, args.fin)
