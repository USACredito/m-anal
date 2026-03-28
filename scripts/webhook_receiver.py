"""
webhook_receiver.py — PARTE 1
Servidor HTTP que recibe webhooks de Fathom, clasifica la llamada
según su tipo y la guarda en la tabla correcta de NocoDB.

Ejecución:
    python scripts/webhook_receiver.py

Exponer con ngrok:
    ngrok http 8080
    → Registrar la URL pública en Fathom como webhook
"""

import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.nocodb_client import crear_registro

PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

TABLA_POR_TIPO = {
    "ventas": "llamadas_ventas",
    "soporte": "llamadas_soporte",
    "onboarding": "llamadas_onboarding",
}


def clasificar_llamada(payload: dict) -> str:
    """
    Determina el tipo de llamada desde el payload de Fathom.
    Busca en campos: 'tipo', 'tags', 'category', etc.
    Retorna: 'ventas' | 'soporte' | 'onboarding' | None
    """
    tipo = payload.get("tipo", "").lower()
    if tipo in TABLA_POR_TIPO:
        return tipo

    # Buscar en tags si es una lista
    tags = payload.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            tag_lower = str(tag).lower()
            if tag_lower in TABLA_POR_TIPO:
                return tag_lower

    # Buscar en campo 'category'
    category = payload.get("category", "").lower()
    if category in TABLA_POR_TIPO:
        return category

    # Nota: Si no se puede clasificar, no se guarda. Ver directiva.
    return None


def parsear_payload(payload: dict) -> dict:
    """
    Extrae y normaliza los campos del webhook de Fathom
    al formato esperado por NocoDB.
    """
    fecha_raw = payload.get("date", payload.get("started_at", ""))
    fecha_obj = None
    hora_str = None

    if fecha_raw:
        try:
            fecha_obj = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
            fecha_str = fecha_obj.strftime("%Y-%m-%d")
            hora_str = fecha_obj.strftime("%H:%M")
        except ValueError:
            fecha_str = fecha_raw
    else:
        fecha_str = datetime.now().strftime("%Y-%m-%d")

    # Participantes pueden venir como lista de objetos o strings
    participantes_raw = payload.get("attendees", payload.get("participants", []))
    if isinstance(participantes_raw, list):
        participantes = []
        for p in participantes_raw:
            if isinstance(p, dict):
                name = p.get("name", p.get("email", str(p)))
                participantes.append(name)
            else:
                participantes.append(str(p))
    else:
        participantes = []

    duracion = payload.get("duration_minutes", payload.get("duration", 0))
    if isinstance(duracion, float):
        duracion = int(duracion)

    return {
        "id_fathom": str(payload.get("id", payload.get("call_id", ""))),
        "titulo": payload.get("title", payload.get("name", "Sin título")),
        "fecha": fecha_str,
        "hora": hora_str or "00:00",
        "duracion_minutos": duracion,
        "participantes": json.dumps(participantes, ensure_ascii=False),
        "url_grabacion": payload.get("recording_url", ""),
        "url_transcripcion_fathom": payload.get("transcript_url", ""),
        "tipo": clasificar_llamada(payload) or "sin_clasificar",
        "estado_procesamiento": "pendiente",
        "transcripcion_texto": "",
        "fecha_procesamiento": None,
    }


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook/fathom":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Payload inválido: {e}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "JSON invalido"}')
            return

        tipo = clasificar_llamada(payload)
        if not tipo:
            print(f"[WARN] Llamada sin tipo reconocido. Payload: {payload}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ignorado", "razon": "tipo no reconocido"}')
            return

        tabla = TABLA_POR_TIPO[tipo]
        datos = parsear_payload(payload)

        try:
            resultado = crear_registro(tabla, datos)
            call_id = datos["id_fathom"]
            print(f"[OK] Llamada {call_id} ({tipo}) guardada en '{tabla}' → ID NocoDB: {resultado.get('Id')}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "nocodb_id": resultado.get("Id")}).encode())
        except Exception as e:
            print(f"[ERROR] No se pudo guardar en NocoDB: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        # Silenciar logs HTTP por defecto, ya manejamos los nuestros
        pass


if __name__ == "__main__":
    print(f"[WEBHOOK] Servidor escuchando en http://0.0.0.0:{PORT}/webhook/fathom")
    print("[WEBHOOK] Usa ngrok para exponer externamente: ngrok http 8080")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WEBHOOK] Servidor detenido.")
