"""
calificaciones.py — PARTE 6
Califica cada llamada usando OpenAI GPT-4o-mini.
- Si Tipo = "setter"  → solo califica setter + lead
- Si Tipo = "closer"  → solo califica closer + lead
- Incluye resumen narrativo de lo que se hizo bien y mal.
- Guarda resultados en NocoDB.

Ejecución:
    python scripts/calificaciones.py --inicio 2025-03-01 --fin 2025-03-07
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import crear_registro, listar_registros
from scripts.agentes_config import clasificar_participante

load_dotenv()

# ─── PROMPTS DE CALIFICACIÓN ──────────────────────────────────────────────────

PROMPT_CALIDAD_SETTER = """
Analiza el desempeño del SETTER (quien busca agendar la cita) en esta transcripción y califica su llamada del 1 al 10 evaluando:
- Rapport y conexión inicial con el prospecto
- Identificación de dolores y necesidades del lead
- Capacidad para "vender" la cita de estrategia
- Manejo de objeciones iniciales
- Profesionalismo y tono de voz (según transcripción)

Responde SOLO con un JSON válido (sin markdown):
{
  "calificacion_total": <número 1-10>,
  "desglose": {
    "rapport": <1-10>,
    "identificacion_dolor": <1-10>,
    "venta_cita": <1-10>,
    "manejo_objeciones": <1-10>
  },
  "agendo_cita": "<sí | no>",
  "nombre_setter": "<nombre del setter si se menciona, sino 'Desconocido'>",
  "puntos_fuertes": ["<máximo 3 puntos concretos de lo que hizo bien, con ejemplo de la llamada>"],
  "areas_mejora": ["<máximo 3 puntos concretos de lo que debe mejorar, con ejemplo de la llamada>"],
  "resumen_ejecutivo": "<2-3 oraciones resumiendo el desempeño general del setter en esta llamada>"
}
"""

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
Analiza el desempeño del CLOSER (quien intenta cerrar la venta) en esta transcripción y califica su llamada del 1 al 10 evaluando:
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
  "puntos_fuertes": ["<máximo 3 puntos concretos de lo que hizo bien, con ejemplo de la llamada>"],
  "areas_mejora": ["<máximo 3 puntos concretos de lo que debe mejorar, con ejemplo de la llamada>"],
  "resumen_ejecutivo": "<2-3 oraciones resumiendo el desempeño general del closer en esta llamada>",
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


def llamar_openai_json(prompt: str, transcripcion: str) -> dict:
    """
    Envía el prompt + transcripción a OpenAI GPT-4o-mini y parsea el JSON.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  [ERROR] OPENAI_API_KEY no encontrada.")
        return {"error": "no_api_key"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Eres un experto en análisis de llamadas de ventas. Siempre respondes en formato JSON puro, sin markdown."},
            {"role": "user", "content": prompt + "\n\nTRANSCRIPCIÓN:\n" + transcripcion}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0
    }

    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"  [ERROR] Al llamar a OpenAI: {e}")
        return {"error": str(e)}


def calificar_ventas(registros: list) -> tuple:
    """
    Califica llamadas de ventas respetando el Tipo (setter/closer).
    Cada llamada solo genera la calificación que corresponde a su tipo.
    Retorna (avg_leads, avg_closers, avg_setters).
    """
    califs_leads = []
    califs_closers = []
    califs_setters = []

    for r in registros:
        duracion_min = r.get("Duración (min)") or r.get("Duración", 0)
        try:
            duracion_min = float(duracion_min or 0)
        except (ValueError, TypeError):
            duracion_min = 0
        if duracion_min < 2:
            print(f"  [SKIP] Llamada {r.get('ID Fathom')} demasiado corta ({duracion_min} min).")
            continue

        transcripcion = r.get("Transcripción Texto", "")
        if not transcripcion:
            continue

        call_id = r.get("ID Fathom", "N/A")
        fecha = r.get("Fecha", "")
        mes_anio = datetime.now().strftime("%Y-%m")

        participantes = r.get("Participantes", "")
        tipo_llamada = (r.get("Tipo") or "").lower()
        partes = [p.strip() for p in participantes.split(",") if p.strip()]
        # Identificar cuál participante es el agente (no siempre es el primero en RC)
        nombre_agente_meta = next(
            (p for p in partes if clasificar_participante(p) != "desconocido"),
            partes[0] if partes else "Desconocido"
        )
        contexto_agente = f"\n\n[CONTEXTO]: El agente que realizó esta llamada se llama: {nombre_agente_meta}."

        print(f"\n  → [{call_id}] Tipo: {tipo_llamada or 'sin definir'}")

        # ── Calificar Lead (siempre, independiente del tipo) ──
        print(f"    Evaluando LEAD...")
        resultado_lead = llamar_openai_json(PROMPT_CALIDAD_LEAD, transcripcion)
        if "error" not in resultado_lead:
            try:
                crear_registro("calificaciones_leads", {
                    "ID Llamada": call_id,
                    "Fecha Llamada": fecha,
                    "Calificación": resultado_lead.get("calificacion", 0),
                    "Nivel": resultado_lead.get("nivel", ""),
                    "Justificación": resultado_lead.get("justificacion", ""),
                    "Positivos": json.dumps(resultado_lead.get("factores_positivos", []), ensure_ascii=False),
                    "Negativos": json.dumps(resultado_lead.get("factores_negativos", []), ensure_ascii=False),
                    "Mes-Año": mes_anio,
                })
                califs_leads.append(resultado_lead.get("calificacion", 0))
            except Exception as e:
                print(f"    [ERROR] No se pudo guardar calificacion_lead: {e}")

        # ── Calificar según Tipo: SETTER o CLOSER ──
        if tipo_llamada in ("setter",):
            print(f"    Evaluando SETTER...")
            resultado_setter = llamar_openai_json(PROMPT_CALIDAD_SETTER, transcripcion + contexto_agente)
            if "error" not in resultado_setter:
                desglose = resultado_setter.get("desglose", {})
                nombre_setter = resultado_setter.get("nombre_setter", "Desconocido")
                if not nombre_setter or nombre_setter == "Desconocido":
                    nombre_setter = nombre_agente_meta
                puntos_fuertes = resultado_setter.get("puntos_fuertes", [])
                areas_mejora = resultado_setter.get("areas_mejora", [])
                resumen = resultado_setter.get("resumen_ejecutivo", "")
                try:
                    payload = {
                        "ID Llamada": call_id,
                        "Setter": nombre_setter,
                        "Nota Total": float(resultado_setter.get("calificacion_total", 0)),
                        "Rapport": float(desglose.get("rapport", 0)),
                        "Identificación Dolor": float(desglose.get("identificacion_dolor", 0)),
                        "Venta Cita": float(desglose.get("venta_cita", 0)),
                        "Objeciones": float(desglose.get("manejo_objeciones", 0)),
                        "Agendó?": str(resultado_setter.get("agendo_cita", "")),
                        "Puntos Fuertes": json.dumps(puntos_fuertes, ensure_ascii=False),
                        "Áreas de Mejora": json.dumps(areas_mejora, ensure_ascii=False),
                        "Resumen": resumen,
                        "Fecha Llamada": fecha,
                        "Mes-Año": mes_anio,
                    }
                    crear_registro("calificaciones_setters", payload)
                    califs_setters.append(float(resultado_setter.get("calificacion_total", 0)))
                    print(f"    [OK] Setter calificado: {nombre_setter} → {resultado_setter.get('calificacion_total')}/10")
                except Exception as e:
                    print(f"    [ERROR] No se pudo guardar calificacion_setter: {e}")

        elif tipo_llamada in ("closer",):
            print(f"    Evaluando CLOSER...")
            resultado_closer = llamar_openai_json(PROMPT_CALIDAD_CLOSER, transcripcion + contexto_agente)
            if "error" not in resultado_closer:
                desglose = resultado_closer.get("desglose", {})
                nombre_closer = resultado_closer.get("nombre_closer", "Desconocido")
                if not nombre_closer or nombre_closer == "Desconocido":
                    nombre_closer = nombre_agente_meta
                puntos_fuertes = resultado_closer.get("puntos_fuertes", [])
                areas_mejora = resultado_closer.get("areas_mejora", [])
                resumen = resultado_closer.get("resumen_ejecutivo", "")
                try:
                    payload_closer = {
                        "ID Llamada": call_id,
                        "Closer": nombre_closer,
                        "Nota Total": float(resultado_closer.get("calificacion_total", 0)),
                        "Rapport": float(desglose.get("rapport", 0)),
                        "Descubrimiento": float(desglose.get("descubrimiento", 0)),
                        "Presentación": float(desglose.get("presentacion", 0)),
                        "Objeciones": float(desglose.get("objeciones", 0)),
                        "Cierre": float(desglose.get("cierre", 0)),
                        "Resultado": str(resultado_closer.get("resultado_llamada", "")),
                        "Puntos Fuertes": json.dumps(puntos_fuertes, ensure_ascii=False),
                        "Áreas de Mejora": json.dumps(areas_mejora, ensure_ascii=False),
                        "Resumen": resumen,
                        "Fecha Llamada": fecha,
                        "Mes-Año": mes_anio,
                    }
                    crear_registro("calificaciones_closers", payload_closer)
                    califs_closers.append(float(resultado_closer.get("calificacion_total", 0)))
                    print(f"    [OK] Closer calificado: {nombre_closer} → {resultado_closer.get('calificacion_total')}/10")
                except Exception as e:
                    print(f"    [ERROR] No se pudo guardar calificacion_closer: {e}")

        else:
            # Tipo desconocido: intentar identificar por contexto (califica ambos)
            print(f"    [WARN] Tipo de llamada desconocido ('{tipo_llamada}'). Calificando como setter y closer.")
            # Setter
            resultado_setter = llamar_openai_json(PROMPT_CALIDAD_SETTER, transcripcion + contexto_agente)
            if "error" not in resultado_setter:
                desglose = resultado_setter.get("desglose", {})
                nombre_setter = resultado_setter.get("nombre_setter", nombre_agente_meta)
                try:
                    crear_registro("calificaciones_setters", {
                        "ID Llamada": call_id,
                        "Setter": nombre_setter,
                        "Nota Total": float(resultado_setter.get("calificacion_total", 0)),
                        "Rapport": float(desglose.get("rapport", 0)),
                        "Identificación Dolor": float(desglose.get("identificacion_dolor", 0)),
                        "Venta Cita": float(desglose.get("venta_cita", 0)),
                        "Objeciones": float(desglose.get("manejo_objeciones", 0)),
                        "Agendó?": str(resultado_setter.get("agendo_cita", "")),
                        "Puntos Fuertes": json.dumps(resultado_setter.get("puntos_fuertes", []), ensure_ascii=False),
                        "Áreas de Mejora": json.dumps(resultado_setter.get("areas_mejora", []), ensure_ascii=False),
                        "Resumen": resultado_setter.get("resumen_ejecutivo", ""),
                        "Fecha Llamada": fecha,
                        "Mes-Año": mes_anio,
                    })
                    califs_setters.append(float(resultado_setter.get("calificacion_total", 0)))
                except Exception as e:
                    print(f"    [ERROR] setter (fallback): {e}")
            # Closer
            resultado_closer = llamar_openai_json(PROMPT_CALIDAD_CLOSER, transcripcion + contexto_agente)
            if "error" not in resultado_closer:
                desglose = resultado_closer.get("desglose", {})
                nombre_closer = resultado_closer.get("nombre_closer", nombre_agente_meta)
                try:
                    crear_registro("calificaciones_closers", {
                        "ID Llamada": call_id,
                        "Closer": nombre_closer,
                        "Nota Total": float(resultado_closer.get("calificacion_total", 0)),
                        "Rapport": float(desglose.get("rapport", 0)),
                        "Descubrimiento": float(desglose.get("descubrimiento", 0)),
                        "Presentación": float(desglose.get("presentacion", 0)),
                        "Objeciones": float(desglose.get("objeciones", 0)),
                        "Cierre": float(desglose.get("cierre", 0)),
                        "Resultado": str(resultado_closer.get("resultado_llamada", "")),
                        "Puntos Fuertes": json.dumps(resultado_closer.get("puntos_fuertes", []), ensure_ascii=False),
                        "Áreas de Mejora": json.dumps(resultado_closer.get("areas_mejora", []), ensure_ascii=False),
                        "Resumen": resultado_closer.get("resumen_ejecutivo", ""),
                        "Fecha Llamada": fecha,
                        "Mes-Año": mes_anio,
                    })
                    califs_closers.append(float(resultado_closer.get("calificacion_total", 0)))
                except Exception as e:
                    print(f"    [ERROR] closer (fallback): {e}")

    avg_leads   = round(sum(califs_leads)   / len(califs_leads),   2) if califs_leads   else 0
    avg_closers = round(sum(califs_closers) / len(califs_closers), 2) if califs_closers else 0
    avg_setters = round(sum(califs_setters) / len(califs_setters), 2) if califs_setters else 0
    return avg_leads, avg_closers, avg_setters


def guardar_resumen_mensual(avg_leads, avg_closers, avg_setters, n_ventas):
    """Guarda el resumen mensual de calidad en NocoDB."""
    mes_anio = datetime.now().strftime("%Y-%m")
    try:
        crear_registro("resumen_mensual_calidad", {
            "Mes-Año": mes_anio,
            "Promedio Leads": avg_leads,
            "Promedio Closers": avg_closers,
            "Promedio Setters": avg_setters,
            "Total Ventas": n_ventas,
        })
        print(f"\n[CALIFICACIONES] Resumen mensual {mes_anio} guardado en NocoDB.")
    except Exception as e:
        print(f"\n[WARN] No se pudo guardar resumen mensual: {e}")


def main():
    parser = argparse.ArgumentParser(description="Calificar llamadas con OpenAI GPT-4o-mini.")
    parser.add_argument("--inicio", help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--fin", help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--semana", action="store_true", help="Calificar desde el lunes de esta semana")
    args = parser.parse_args()

    hoy = datetime.now()
    if args.semana:
        lunes = hoy - timedelta(days=hoy.weekday())
        args.inicio = lunes.strftime("%Y-%m-%d")
        args.fin = hoy.strftime("%Y-%m-%d")
    elif not args.inicio or not args.fin:
        parser.error("Debes especificar --inicio y --fin, o usar --semana")

    print(f"[CALIFICACIONES] Procesando: {args.inicio} → {args.fin}")

    def get_registros(tabla):
        try:
            regs = listar_registros(tabla, where="(Estado,eq,transcrito)")
            return [r for r in regs if args.inicio <= r.get("Fecha", "") <= args.fin]
        except Exception as e:
            print(f"  [WARN] No se pudo leer {tabla}: {e}")
            return []

    regs_ventas = get_registros("llamadas_ventas")

    # Desglose por tipo
    setters_count = sum(1 for r in regs_ventas if (r.get("Tipo") or "").lower() == "setter")
    closers_count = sum(1 for r in regs_ventas if (r.get("Tipo") or "").lower() == "closer")
    otros_count   = len(regs_ventas) - setters_count - closers_count

    print(f"\n[CALIFICACIONES] Llamadas encontradas: {len(regs_ventas)}")
    print(f"  → Setters: {setters_count} | Closers: {closers_count} | Sin tipo: {otros_count}")

    avg_leads, avg_closers, avg_setters = 0, 0, 0
    if regs_ventas:
        print("\n[CALIFICACIONES] → Calificando VENTAS...")
        avg_leads, avg_closers, avg_setters = calificar_ventas(regs_ventas)

    guardar_resumen_mensual(avg_leads, avg_closers, avg_setters, len(regs_ventas))

    print(f"\n[CALIFICACIONES] ✅ Promedios del período:")
    print(f"  Calidad Leads (Marketing): {avg_leads}/10")
    print(f"  Calidad Setters:           {avg_setters}/10")
    print(f"  Calidad Closers:           {avg_closers}/10")


if __name__ == "__main__":
    main()
