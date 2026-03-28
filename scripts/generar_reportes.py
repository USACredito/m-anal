"""
generar_reportes.py — PARTE 4
Lee los análisis de Gemini y genera PDFs formateados por categoría.
Produce reportes para ventas (2 docs), soporte (1 doc) y onboarding (1 doc).

Ejecución:
    python scripts/generar_reportes.py --inicio 2025-03-01 --fin 2025-03-07
"""

import argparse
import os
import sys
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros

load_dotenv()

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
REPORTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reportes")
os.makedirs(REPORTES_DIR, exist_ok=True)

# ─── ESTILOS PDF ─────────────────────────────────────────────────────────────

def crear_estilos():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Titulo",
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a2744"),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Subtitulo",
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=10,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Cuerpo",
        fontSize=10,
        fontName="Helvetica",
        leading=14,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Metadata",
        fontSize=9,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#64748b"),
        spaceAfter=4,
    ))
    return styles


def leer_analisis(categoria: str, fecha_inicio: str, fecha_fin: str) -> str:
    nombre = f"analisis_{categoria}_{fecha_inicio}_{fecha_fin}.txt"
    ruta = os.path.join(TMP_DIR, nombre)
    if not os.path.exists(ruta):
        return f"[Análisis no disponible para {categoria}. Ejecuta primero analisis_gemini.py]"
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def contar_llamadas(categoria: str, fecha_inicio: str, fecha_fin: str) -> int:
    try:
        tabla = f"llamadas_{categoria}"
        registros = listar_registros(tabla, where="(estado_procesamiento,eq,transcrito)")
        filtrados = [r for r in registros if fecha_inicio <= r.get("fecha", "") <= fecha_fin]
        return len(filtrados)
    except Exception:
        return 0


def crear_encabezado(story, styles, titulo: str, subtitulo: str, fecha_inicio: str, fecha_fin: str):
    """Añade el encabezado estándar al PDF."""
    story.append(Paragraph(titulo, styles["Titulo"]))
    story.append(Paragraph(subtitulo, styles["Metadata"]))
    story.append(Paragraph(
        f"Período: <b>{fecha_inicio}</b> al <b>{fecha_fin}</b>",
        styles["Metadata"]
    ))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Metadata"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Línea separadora como tabla de 1 celda
    separador = Table([["─" * 80]], colWidths=[17 * cm])
    separador.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#e2e8f0")),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
    ]))
    story.append(separador)
    story.append(Spacer(1, 0.4 * cm))


def texto_a_parrafos(texto: str, styles) -> list:
    """Convierte el texto del análisis de Gemini en párrafos formateados."""
    elementos = []
    for linea in texto.split("\n"):
        linea = linea.strip()
        if not linea:
            elementos.append(Spacer(1, 0.2 * cm))
            continue

        if linea.startswith("**") and linea.endswith("**"):
            texto_limpio = linea.strip("**").strip("#").strip()
            elementos.append(Paragraph(texto_limpio, styles["Subtitulo"]))
        elif linea.startswith("##") or linea.startswith("#"):
            texto_limpio = linea.strip("#").strip()
            elementos.append(Paragraph(texto_limpio, styles["Subtitulo"]))
        elif linea.startswith("- ") or linea.startswith("* "):
            texto_limpio = "• " + linea[2:]
            elementos.append(Paragraph(texto_limpio, styles["Cuerpo"]))
        else:
            elementos.append(Paragraph(linea, styles["Cuerpo"]))

    return elementos


def generar_reporte_ventas(fecha_inicio: str, fecha_fin: str) -> list:
    """Genera los 2 reportes de ventas."""
    styles = crear_estilos()
    archivos = []
    analisis = leer_analisis("ventas", fecha_inicio, fecha_fin)
    n_llamadas = contar_llamadas("ventas", fecha_inicio, fecha_fin)

    # Documento 1: Errores + Ofertas + Promesas
    nombre1 = f"reporte_errores_ventas_{fecha_inicio}_{fecha_fin}.pdf"
    ruta1 = os.path.join(REPORTES_DIR, nombre1)
    doc1 = SimpleDocTemplate(ruta1, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story1 = []
    crear_encabezado(story1, styles, "REPORTE DE ERRORES DE VENTAS", "Análisis de calidad de llamadas de ventas", fecha_inicio, fecha_fin)

    # Tabla de resumen
    tabla_resumen = Table([
        ["Total llamadas analizadas", str(n_llamadas)],
    ], colWidths=[12*cm, 5*cm])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story1.append(tabla_resumen)
    story1.append(Spacer(1, 0.5*cm))

    story1.extend(texto_a_parrafos(analisis, styles))
    doc1.build(story1)
    archivos.append(ruta1)
    print(f"  → PDF generado: {ruta1}")

    # Documento 2: Reporte Marketing (reutiliza el análisis de ventas, enfocado en señales de prospecto)
    nombre2 = f"reporte_marketing_{fecha_inicio}_{fecha_fin}.pdf"
    ruta2 = os.path.join(REPORTES_DIR, nombre2)
    doc2 = SimpleDocTemplate(ruta2, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story2 = []
    crear_encabezado(story2, styles, "REPORTE DE INTELIGENCIA DE MARKETING", "Señales de prospectos y patrones de conversión", fecha_inicio, fecha_fin)
    story2.extend(texto_a_parrafos(analisis, styles))
    doc2.build(story2)
    archivos.append(ruta2)
    print(f"  → PDF generado: {ruta2}")

    return archivos


def generar_reporte_soporte(fecha_inicio: str, fecha_fin: str) -> list:
    """Genera el reporte de soporte."""
    styles = crear_estilos()
    analisis = leer_analisis("soporte", fecha_inicio, fecha_fin)
    n_llamadas = contar_llamadas("soporte", fecha_inicio, fecha_fin)

    nombre = f"reporte_soporte_{fecha_inicio}_{fecha_fin}.pdf"
    ruta = os.path.join(REPORTES_DIR, nombre)
    doc = SimpleDocTemplate(ruta, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    crear_encabezado(story, styles, "REPORTE DE CALIDAD — SOPORTE", "Análisis de llamadas de soporte al cliente", fecha_inicio, fecha_fin)

    tabla_resumen = Table([
        ["Total llamadas analizadas", str(n_llamadas)],
    ], colWidths=[12*cm, 5*cm])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 0.5*cm))

    story.extend(texto_a_parrafos(analisis, styles))
    doc.build(story)
    print(f"  → PDF generado: {ruta}")
    return [ruta]


def generar_reporte_onboarding(fecha_inicio: str, fecha_fin: str) -> list:
    """Genera el reporte de onboarding."""
    styles = crear_estilos()
    analisis = leer_analisis("onboarding", fecha_inicio, fecha_fin)
    n_llamadas = contar_llamadas("onboarding", fecha_inicio, fecha_fin)

    nombre = f"reporte_onboarding_{fecha_inicio}_{fecha_fin}.pdf"
    ruta = os.path.join(REPORTES_DIR, nombre)
    doc = SimpleDocTemplate(ruta, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    crear_encabezado(story, styles, "REPORTE DE CALIDAD — ONBOARDING", "Evaluación de coaches y sesiones de onboarding", fecha_inicio, fecha_fin)

    tabla_resumen = Table([
        ["Total llamadas analizadas", str(n_llamadas)],
    ], colWidths=[12*cm, 5*cm])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 0.5*cm))

    story.extend(texto_a_parrafos(analisis, styles))
    doc.build(story)
    print(f"  → PDF generado: {ruta}")
    return [ruta]


def main():
    parser = argparse.ArgumentParser(description="Generar reportes PDF.")
    parser.add_argument("--inicio", required=True, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--fin", required=True, help="Fecha fin (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"[REPORTES] Generando PDFs para: {args.inicio} → {args.fin}")

    print("\n[REPORTES] → Ventas")
    generar_reporte_ventas(args.inicio, args.fin)

    print("\n[REPORTES] → Soporte")
    generar_reporte_soporte(args.inicio, args.fin)

    print("\n[REPORTES] → Onboarding")
    generar_reporte_onboarding(args.inicio, args.fin)

    print(f"\n[REPORTES] ✅ PDFs guardados en: {REPORTES_DIR}")


if __name__ == "__main__":
    main()
