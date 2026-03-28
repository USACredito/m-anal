"""
calificaciones.py — PARTE 6
Califica cada llamada usando Gemini (leads, closers, onboarding)
y guarda los resultados en NocoDB. También calcula el resumen mensual.

Ejecución:
    python scripts/calificaciones.py --inicio 2025-03-01 --fin 2025-03-07
"""

import argparse
import json
import os
import sys
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import crear_registro, listar_registros

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

# ─── PROMPTS DE CALIFICACIÓN ──────────────────────────────────────────────────

PROMPT_CALIDAD_LEAD = """
Basándote en la transcripción de esta llamada de ventas, evalúa la calidad del lead del 1 al 10 considerando:
- Nivel de interés demostrado
- Capacidad de decisión (¿habla con el tomador de decisiones?)
- Fit con el producto (¿tiene el problema que resolvemos?)
- Urgencia expresada
- Presupuesto aproximado (si se mencionó)

Responde SOLO con un JSON válido (sin markdown, sin explicaciones adicionales):
{
  "calificacion": <número 1-10>,
  "nivel": "<frio | tibio | caliente>",
  "justificacion": "<máximo 3 oraciones>",
  "factores_positivos": ["...", "..."],
  "factores_negativos": ["...", "..."]
}

TRANSCRIPCIÓN:
"""

PROMPT_CALIDAD_CLOSER = """
Analiza el desempeño del closer en esta transcripción y califica su llamada del 1 al 10 evaluando:
- Rapport inicial y conexión con el prospecto
- Identificación de necesidades y dolor
- Presentación del producto/servicio
- Manejo de objeciones
- Técnica de cierre utilizada
- Profesionalismo y confianza transmitida

Responde SOLO con un JSON válido (sin markdown, sin explicaciones adicionales):
{
  "calificacion_total": <número 1-10>,
  "desglose": {
    "rapport": <1-10>,
    "descubrimiento": <1-10>,
    "presentacion": <1-10>,
    "objeciones": <1-10>,
    "cierre": <1-10>
  },
  "fortalezas": ["...", "..."],
  "areas_mejora": ["...", "..."],
  "resultado_llamada": "<vendió | no vendió | seguimiento pendiente>",
  "nombre_closer": "<nombre si se menciona, sino 'Desconocido'>"
}

TRANSCRIPCIÓN:
"""

PROMPT_CALIDAD_ONBOARDING = """
Analiza el desempeño del coach en esta transcripción de onboarding y califica del 1 al 10 evaluando:
- Claridad en las explicaciones
- Adaptación al nivel del cliente
- Completitud del onboarding (¿se cubrió todo?)
- Manejo del tiempo
- Satisfacción aparente del cliente al final
- Resolución de dudas durante la sesión

Responde SOLO con un JSON válido (sin markdown, sin explicaciones adicionales):
{
  "calificacion_total": <número 1-10>,
  "desglose": {
    "claridad": <1-10>,
    "adaptacion": <1-10>,
    "completitud": <1-10>,
    "manejo_tiempo": <1-10>,
    "satisfaccion_cliente": <1-10>
  },
  "logros": ["...", "..."],
  "errores_detectados": ["...", "..."],
  "cliente_listo_para_usar": "<sí | no | parcialmente>",
  "nombre_coach": "<nombre si se menciona, sino 'Desconocido'>"
}

TRANSCRIPCIÓN:
"""


def llamar_gemini_json(prompt: str, transcripcion: str) -> dict:
    """
    Envía el prompt + transcripción a Gemini y parsea el JSON de respuesta.
    Nota: Si Gemini no responde JSON puro, se intenta extraer el bloque JSON.
    """
    texto_completo = prompt + "\n\n" + transcripcion

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(texto_completo)
    texto_respuesta = response.text.strip()

    # Intentar parsear directo
    try:
        return json.loads(texto_respuesta)
    except json.JSONDecodeError:
        pass

    # Intentar extraer bloque JSON si viene con markdown
    inicio = texto_respuesta.find("{")
    fin = texto_respuesta.rfind("}") + 1
    if inicio != -1 and fin > inicio:
        try:
            return json.loads(texto_respuesta[inicio:fin])
        except json.JSONDecodeError:
            pass

    # Fallback: retornar texto como error
    print(f"  [WARN] No se pudo parsear JSON de Gemini. Respuesta: {texto_respuesta[:200]}")
    return {"error": texto_respuesta}


def calificar_ventas(registros: list) -> tuple[float, float]:
    """Califica leads y closers para llamadas de ventas. Retorna (avg_leads, avg_closers)."""
    califs_leads = []
    califs_closers = []

    for r in registros:
        transcripcion = r.get("transcripcion_texto", "")
        if not transcripcion:
            continue

        call_id = r.get("id_fathom", "N/A")
        fecha = r.get("fecha", "")
        mes_anio = datetime.now().strftime("%Y-%m")

        # ── Calificar Lead ──
        print(f"  → [{call_id}] Calificando lead...")
        resultado_lead = llamar_gemini_json(PROMPT_CALIDAD_LEAD, transcripcion)
        if "error" not in resultado_lead:
            try:
                crear_registro("calificaciones_leads", {
                    "id_llamada_fathom": call_id,
                    "fecha_llamada": fecha,
                    "fecha_calificacion": datetime.now().strftime("%Y-%m-%d"),
                    "calificacion": resultado_lead.get("calificacion", 0),
                    "nivel": resultado_lead.get("nivel", ""),
                    "justificacion": resultado_lead.get("justificacion", ""),
                    "factores_positivos": json.dumps(resultado_lead.get("factores_positivos", []), ensure_ascii=False),
                    "factores_negativos": json.dumps(resultado_lead.get("factores_negativos", []), ensure_ascii=False),
                    "mes_año": mes_anio,
                })
                califs_leads.append(resultado_lead.get("calificacion", 0))
            except Exception as e:
                print(f"  [ERROR] No se pudo guardar calificacion_lead: {e}")

        # ── Calificar Closer ──
        print(f"  → [{call_id}] Calificando closer...")
        resultado_closer = llamar_gemini_json(PROMPT_CALIDAD_CLOSER, transcripcion)
        if "error" not in resultado_closer:
            desglose = resultado_closer.get("desglose", {})
            try:
                crear_registro("calificaciones_closers", {
                    "id_llamada_fathom": call_id,
                    "fecha_llamada": fecha,
                    "fecha_calificacion": datetime.now().strftime("%Y-%m-%d"),
                    "nombre_closer": resultado_closer.get("nombre_closer", "Desconocido"),
                    "calificacion_total": resultado_closer.get("calificacion_total", 0),
                    "calificacion_rapport": desglose.get("rapport", 0),
                    "calificacion_descubrimiento": desglose.get("descubrimiento", 0),
                    "calificacion_presentacion": desglose.get("presentacion", 0),
                    "calificacion_objeciones": desglose.get("objeciones", 0),
                    "calificacion_cierre": desglose.get("cierre", 0),
                    "fortalezas": json.dumps(resultado_closer.get("fortalezas", []), ensure_ascii=False),
                    "areas_mejora": json.dumps(resultado_closer.get("areas_mejora", []), ensure_ascii=False),
                    "resultado": resultado_closer.get("resultado_llamada", ""),
                    "mes_año": mes_anio,
                })
                califs_closers.append(resultado_closer.get("calificacion_total", 0))
            except Exception as e:
                print(f"  [ERROR] No se pudo guardar calificacion_closer: {e}")

    avg_leads = round(sum(califs_leads) / len(califs_leads), 2) if califs_leads else 0
    avg_closers = round(sum(califs_closers) / len(califs_closers), 2) if califs_closers else 0
    return avg_leads, avg_closers


def calificar_onboarding(registros: list) -> float:
    """Califica sesiones de onboarding. Retorna el promedio."""
    califs = []

    for r in registros:
        transcripcion = r.get("transcripcion_texto", "")
        if not transcripcion:
            continue

        call_id = r.get("id_fathom", "N/A")
        fecha = r.get("fecha", "")
        mes_anio = datetime.now().strftime("%Y-%m")

        print(f"  → [{call_id}] Calificando onboarding...")
        resultado = llamar_gemini_json(PROMPT_CALIDAD_ONBOARDING, transcripcion)
        if "error" not in resultado:
            desglose = resultado.get("desglose", {})
            try:
                crear_registro("calificaciones_onboarding", {
                    "id_llamada_fathom": call_id,
                    "fecha_llamada": fecha,
                    "fecha_calificacion": datetime.now().strftime("%Y-%m-%d"),
                    "nombre_coach": resultado.get("nombre_coach", "Desconocido"),
                    "calificacion_total": resultado.get("calificacion_total", 0),
                    "calificacion_claridad": desglose.get("claridad", 0),
                    "calificacion_adaptacion": desglose.get("adaptacion", 0),
                    "calificacion_completitud": desglose.get("completitud", 0),
                    "calificacion_tiempo": desglose.get("manejo_tiempo", 0),
                    "calificacion_satisfaccion": desglose.get("satisfaccion_cliente", 0),
                    "logros": json.dumps(resultado.get("logros", []), ensure_ascii=False),
                    "errores_detectados": json.dumps(resultado.get("errores_detectados", []), ensure_ascii=False),
                    "cliente_listo": resultado.get("cliente_listo_para_usar", ""),
                    "mes_año": mes_anio,
                })
                califs.append(resultado.get("calificacion_total", 0))
            except Exception as e:
                print(f"  [ERROR] No se pudo guardar calificacion_onboarding: {e}")

    return round(sum(califs) / len(califs), 2) if califs else 0


def guardar_resumen_mensual(avg_leads, avg_closers, avg_onboarding,
                             n_ventas, n_soporte, n_onboarding):
    """Guarda el resumen mensual de calidad en NocoDB."""
    mes_anio = datetime.now().strftime("%Y-%m")
    try:
        crear_registro("resumen_mensual_calidad", {
            "mes_año": mes_anio,
            "promedio_calidad_leads": avg_leads,
            "promedio_calidad_closers": avg_closers,
            "promedio_calidad_onboarding": avg_onboarding,
            "total_llamadas_ventas": n_ventas,
            "total_llamadas_soporte": n_soporte,
            "total_llamadas_onboarding": n_onboarding,
            "fecha_calculo": datetime.now().strftime("%Y-%m-%d"),
        })
        print(f"\n[CALIFICACIONES] Resumen mensual {mes_anio} guardado en NocoDB.")
    except Exception as e:
        print(f"\n[WARN] No se pudo guardar resumen mensual: {e}")


def main():
    parser = argparse.ArgumentParser(description="Calificar llamadas con Gemini.")
    parser.add_argument("--inicio", required=True, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--fin", required=True, help="Fecha fin (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"[CALIFICACIONES] Procesando: {args.inicio} → {args.fin}")

    # Obtener registros transcriptos del rango
    def get_registros(tabla):
        try:
            regs = listar_registros(tabla, where="(estado_procesamiento,eq,transcrito)")
            return [r for r in regs if args.inicio <= r.get("fecha", "") <= args.fin]
        except Exception as e:
            print(f"  [WARN] No se pudo leer {tabla}: {e}")
            return []

    regs_ventas = get_registros("llamadas_ventas")
    regs_soporte = get_registros("llamadas_soporte")
    regs_onboarding = get_registros("llamadas_onboarding")

    print(f"\n[CALIFICACIONES] Ventas: {len(regs_ventas)} | Soporte: {len(regs_soporte)} | Onboarding: {len(regs_onboarding)}")

    # Calificar ventas
    avg_leads, avg_closers = 0, 0
    if regs_ventas:
        print("\n[CALIFICACIONES] → Calificando VENTAS...")
        avg_leads, avg_closers = calificar_ventas(regs_ventas)

    # Calificar onboarding
    avg_onboarding = 0
    if regs_onboarding:
        print("\n[CALIFICACIONES] → Calificando ONBOARDING...")
        avg_onboarding = calificar_onboarding(regs_onboarding)

    # Guardar resumen mensual
    guardar_resumen_mensual(
        avg_leads, avg_closers, avg_onboarding,
        len(regs_ventas), len(regs_soporte), len(regs_onboarding)
    )

    print(f"\n[CALIFICACIONES] ✅ Promedios del período:")
    print(f"  Calidad Leads: {avg_leads}/10")
    print(f"  Calidad Closers: {avg_closers}/10")
    print(f"  Calidad Onboarding: {avg_onboarding}/10")


if __name__ == "__main__":
    main()
