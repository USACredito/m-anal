"""
enviar_slack.py — Nueva Integración
Lee los análisis semanales directamente desde la carpeta .tmp/ generada
por analisis_gemini.py y los envía vía Webhook directamente a Slack.

Porciones que antes iban por email en reportes PDF ahora van en texto enriquecido.
"""

import argparse
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")

def enviar_mensaje_slack(titulo, contenido):
    if not SLACK_WEBHOOK_URL:
        print("[SLACK] ERROR: No se encontró SLACK_WEBHOOK_URL en el archivo .env. Ignorando envío.")
        return False
    
    # Slack limits payload texts to 3000 chars roughly per block, but text can handle up to 4000
    # Cortar si es demasiado masivo
    if len(contenido) > 3500:
        contenido = contenido[:3500] + "\n\n...[mensaje truncado por longitud máxima de Slack]..."

    payload = {
        "text": f"*{titulo}*\n\n{contenido}"
    }

    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload)
        if resp.status_code == 200:
            print(f"[SLACK] ✅ Reporte '{titulo}' enviado exitosamente.")
            return True
        else:
            print(f"[SLACK] ❌ Error enviando a Slack: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[SLACK] ❌ Error de conexión: {e}")
        return False

def enviar_reportes(inicio, fin):
    print(f"\n[SLACK] Preparando envíos de análisis. Periodo: {inicio} a {fin}")

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
            titulo = f"📊 Análisis de Ventas/Marketing: {inicio} → {fin}"
            enviar_mensaje_slack(titulo, texto)

    # Enviar reporte Soporte
    ruta_soporte = os.path.join(TMP_DIR, archivo_soporte)
    if os.path.exists(ruta_soporte):
        with open(ruta_soporte, "r", encoding="utf-8") as f:
            texto = f.read()
        titulo = f"🎧 Análisis de Soporte: {inicio} → {fin}"
        enviar_mensaje_slack(titulo, texto)

    # Enviar reporte Onboarding
    ruta_onboarding = os.path.join(TMP_DIR, archivo_onboarding)
    if os.path.exists(ruta_onboarding):
        with open(ruta_onboarding, "r", encoding="utf-8") as f:
            texto = f.read()
        titulo = f"🚀 Análisis de Onboarding: {inicio} → {fin}"
        enviar_mensaje_slack(titulo, texto)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fin", required=True)
    args = parser.parse_args()

    enviar_reportes(args.inicio, args.fin)
