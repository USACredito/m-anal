"""
enviar_emails.py — PARTE 5
Obtiene la lista de destinatarios desde NocoDB y envía los PDFs
correspondientes según los permisos de cada email.
También actualiza el estado de las llamadas y registra el log de envíos.

Ejecución:
    python scripts/enviar_emails.py --inicio 2025-03-01 --fin 2025-03-07
"""

import argparse
import json
import os
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import crear_registro, listar_registros, actualizar_registro

load_dotenv()

EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

REPORTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reportes")


def obtener_lista_emails() -> list:
    """Obtiene todos los destinatarios desde la tabla lista_emails de NocoDB."""
    try:
        return listar_registros("lista_emails")
    except Exception as e:
        print(f"[WARN] No se pudo obtener lista de emails: {e}")
        return []


def obtener_archivos_reporte(categoria: str, fecha_inicio: str, fecha_fin: str) -> list:
    """Retorna las rutas de los PDFs correspondientes a una categoría."""
    archivos = {
        "ventas": [
            f"reporte_errores_ventas_{fecha_inicio}_{fecha_fin}.pdf",
            f"reporte_marketing_{fecha_inicio}_{fecha_fin}.pdf",
        ],
        "soporte": [
            f"reporte_soporte_{fecha_inicio}_{fecha_fin}.pdf",
        ],
        "onboarding": [
            f"reporte_onboarding_{fecha_inicio}_{fecha_fin}.pdf",
        ],
    }

    rutas = []
    for nombre in archivos.get(categoria, []):
        ruta = os.path.join(REPORTES_DIR, nombre)
        if os.path.exists(ruta):
            rutas.append(ruta)
        else:
            print(f"  [WARN] Archivo no encontrado: {ruta}")

    return rutas


def crear_email(destinatario: dict, categoria: str, archivos: list, fecha_inicio: str, fecha_fin: str) -> MIMEMultipart:
    """Construye el mensaje de email con los adjuntos correspondientes."""
    nombre = destinatario.get("nombre", "Equipo")
    email = destinatario.get("email", "")

    categoria_capitalizada = categoria.capitalize()
    asunto = f"📊 Reporte de {categoria_capitalizada} — {fecha_inicio} al {fecha_fin}"

    nombres_adjuntos = "\n".join([f"  - {os.path.basename(a)}" for a in archivos])

    cuerpo = f"""Hola {nombre},

Te adjunto el reporte de {categoria_capitalizada} correspondiente al período {fecha_inicio} al {fecha_fin}.

📎 Archivos adjuntos:
{nombres_adjuntos}

Este reporte fue generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M')}.

Si tienes preguntas, responde este correo.

— Sistema de Análisis Automatizado
"""

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = email
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    for ruta_archivo in archivos:
        with open(ruta_archivo, "rb") as f:
            adjunto = MIMEBase("application", "octet-stream")
            adjunto.set_payload(f.read())
            encoders.encode_base64(adjunto)
            adjunto.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(ruta_archivo),
            )
            msg.attach(adjunto)

    return msg


def enviar_email(msg: MIMEMultipart) -> bool:
    """Envía un email usando SMTP. Retorna True si fue exitoso."""
    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"  [ERROR] Fallo al enviar a {msg['To']}: {e}")
        return False


def marcar_llamadas_como_reportadas(fecha_inicio: str, fecha_fin: str):
    """Actualiza el estado de todas las llamadas procesadas a 'reportado'."""
    tablas = ["llamadas_ventas", "llamadas_soporte", "llamadas_onboarding"]
    for tabla in tablas:
        try:
            registros = listar_registros(tabla, where="(Estado,eq,transcrito)")
            filtrados = [r for r in registros if fecha_inicio <= r.get("Fecha", "") <= fecha_fin]
            for r in filtrados:
                actualizar_registro(tabla, r["Id"], {"Estado": "reportado"})
            if filtrados:
                print(f"  → {len(filtrados)} llamadas en '{tabla}' marcadas como 'reportado'")
        except Exception as e:
            print(f"  [WARN] No se pudo actualizar {tabla}: {e}")


def registrar_log_envio(
    fecha_inicio: str, fecha_fin: str, emails_enviados: int, reportes: list, estado: str
):
    """Registra el log del envío en la tabla log_envios de NocoDB."""
    try:
        crear_registro("log_envios", {
            "fecha_envio": datetime.now().strftime("%Y-%m-%d"),
            "periodo_inicio": fecha_inicio,
            "periodo_fin": fecha_fin,
            "emails_enviados": emails_enviados,
            "reportes_generados": json.dumps(reportes),
            "estado": estado,
        })
        print(f"  → Log de envío registrado en NocoDB.")
    except Exception as e:
        print(f"  [WARN] No se pudo registrar log: {e}")


def main():
    parser = argparse.ArgumentParser(description="Enviar reportes por email.")
    parser.add_argument("--inicio", required=True, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--fin", required=True, help="Fecha fin (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"[EMAIL] Enviando reportes: {args.inicio} → {args.fin}")

    destinatarios = obtener_lista_emails()
    if not destinatarios:
        print("[EMAIL] No hay destinatarios en lista_emails. Abortando.")
        return

    print(f"[EMAIL] {len(destinatarios)} destinatarios encontrados.")

    emails_enviados = 0
    reportes_generados = []

    categorias = {
        "ventas": "Ventas",
        "soporte": "Soporte",
        "onboarding": "Onboarding",
    }

    for dest in destinatarios:
        nombre = dest.get("Nombre", "Usuario")
        email = dest.get("Email", "")

        if not email:
            continue

        print(f"\n[EMAIL] → {nombre} ({email})")

        for categoria, campo_permiso in categorias.items():
            # Aceptar true/True/"true"/1 como habilitado
            permiso = dest.get(campo_permiso, False)
            if str(permiso).lower() not in ("true", "1", "yes"):
                continue

            archivos = obtener_archivos_reporte(categoria, args.inicio, args.fin)
            if not archivos:
                print(f"  → Sin reportes de {categoria} disponibles.")
                continue

            msg = crear_email(dest, categoria, archivos, args.inicio, args.fin)
            exito = enviar_email(msg)

            if exito:
                emails_enviados += 1
                reportes_generados.extend([os.path.basename(a) for a in archivos])
                print(f"  → Reporte de {categoria} enviado ✅")
            else:
                print(f"  → Error enviando reporte de {categoria} ❌")

    # Post-procesamiento
    print(f"\n[EMAIL] Marcando llamadas como 'reportado'...")
    marcar_llamadas_como_reportadas(args.inicio, args.fin)

    estado = "exitoso" if emails_enviados > 0 else "sin_envios"
    registrar_log_envio(args.inicio, args.fin, emails_enviados, list(set(reportes_generados)), estado)

    print(f"\n[EMAIL] ✅ Total emails enviados: {emails_enviados}")


if __name__ == "__main__":
    main()
