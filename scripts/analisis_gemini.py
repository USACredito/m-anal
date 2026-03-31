"""
analisis_gemini.py — PARTE 3
Lee los archivos de transcripción generados y los envía a Google Gemini
con los prompts específicos por categoría. Guarda el análisis en archivos
.txt en .tmp/ para ser usados por el generador de reportes.

Ejecución:
    python scripts/analisis_gemini.py --inicio 2025-03-01 --fin 2025-03-07
"""

import argparse
import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash-latest"  # Modelo rápido y económico para análisis de texto

# ─── SYSTEM PROMPTS POR CATEGORÍA ───────────────────────────────────────────

PROMPT_VENTAS = """
Eres un analista experto en ventas consultivas. Analiza las siguientes transcripciones de llamadas de ventas y genera un reporte detallado con los siguientes apartados:

**SECCIÓN 1 - ERRORES DE VENTAS:**
- Lista todos los errores técnicos de ventas identificados (falta de manejo de objeciones, cierre débil, no identificar pain points, falta de urgencia, etc.)
- Para cada error: describe el error, cita el fragmento exacto de la llamada donde ocurrió, y sugiere cómo mejorarlo.

**SECCIÓN 2 - OFERTAS MAL HECHAS:**
- Identifica todas las ocasiones donde la oferta fue presentada de manera incorrecta, incompleta o confusa.
- Señala si se omitió información clave, si el pricing fue mal comunicado, o si los beneficios no fueron bien articulados.

**SECCIÓN 3 - PROMESAS INDEBIDAS:**
- Detecta cualquier promesa que el vendedor haya hecho que no debería comprometerse (plazos irreales, funcionalidades no existentes, descuentos no autorizados, garantías exageradas).
- Cita textualmente cada promesa indebida y clasifícala por nivel de riesgo: ALTO / MEDIO / BAJO.

Sé específico, cita ejemplos textuales, y proporciona sugerencias accionables.

**TRANSCRIPCIONES A ANALIZAR:**
"""

PROMPT_SOPORTE = """
Eres un analista experto en servicio al cliente y soporte técnico. Analiza las siguientes transcripciones de llamadas de soporte y genera un reporte detallado con los siguientes apartados:

**SECCIÓN 1 - PREGUNTAS FRECUENTES:**
- Agrupa y lista todas las preguntas que los clientes repitieron durante las llamadas.
- Ordénalas de mayor a menor frecuencia.
- Para cada una, sugiere si debería existir documentación, un FAQ, o un tutorial que la resuelva.

**SECCIÓN 2 - DUDAS RECURRENTES:**
- Identifica las dudas conceptuales que los clientes tienen sobre el producto/servicio.
- Clasifícalas por área: uso del producto, facturación, funcionalidades, procesos internos, etc.

**SECCIÓN 3 - LO QUE SE HACE BIEN:**
- Detecta momentos en las llamadas donde el agente de soporte manejó excelentemente la situación.
- Cita ejemplos específicos y explica por qué fue una buena práctica.

**SECCIÓN 4 - ÁREAS DE MEJORA EN SOPORTE:**
- Lista los errores o malas prácticas identificadas en el equipo de soporte.
- Para cada una, sugiere qué entrenamiento o proceso mejoraría la situación.

Sé analítico, constructivo y basado en evidencia de las transcripciones.

**TRANSCRIPCIONES A ANALIZAR:**
"""

PROMPT_ONBOARDING = """
Eres un analista experto en customer success y onboarding. Analiza las siguientes transcripciones de llamadas de onboarding y genera un reporte detallado con los siguientes apartados:

**SECCIÓN 1 - EVALUACIÓN DE PROFESORES/COACHES:**
- Analiza el desempeño de cada persona que condujo el onboarding.
- Identifica: claridad en la explicación, manejo del tiempo, adaptación al nivel del cliente, resolución de dudas.
- Lista específicamente qué hicieron mal o podrían mejorar.

**SECCIÓN 2 - CALIFICACIONES POR LLAMADA:**
- Asigna una calificación del 1 al 10 a cada llamada de onboarding analizada.
- Justifica la calificación con base en: efectividad pedagógica, satisfacción del cliente, completitud del onboarding.
- Formato:
  - ID Llamada: [id]
  - Calificación: [X/10]
  - Justificación: [texto]

**SECCIÓN 3 - PUNTOS DE FRICCIÓN DEL CLIENTE:**
- ¿En qué partes del onboarding los clientes se confundieron más?
- ¿Qué conceptos o pasos necesitan ser simplificados o rediseñados?

**SECCIÓN 4 - MEJORES PRÁCTICAS IDENTIFICADAS:**
- ¿Qué técnicas o enfoques funcionaron especialmente bien?
- ¿Qué deberían replicar todos los coaches?

Proporciona análisis accionables que permitan mejorar el proceso de onboarding.

**TRANSCRIPCIONES A ANALIZAR:**
"""

PROMPTS = {
    "ventas": PROMPT_VENTAS,
    "soporte": PROMPT_SOPORTE,
    "onboarding": PROMPT_ONBOARDING,
}


def analizar_con_gemini(categoria: str, transcripciones_texto: str) -> str:
    """
    Envía el texto de transcripciones a Gemini con el prompt de la categoría.
    Retorna el análisis en texto.
    """
    if not transcripciones_texto.strip():
        return f"[Sin transcripciones disponibles para {categoria}]"

    prompt = PROMPTS[categoria] + "\n\n" + transcripciones_texto

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)

    return response.text


def procesar_categoria(categoria: str, fecha_inicio: str, fecha_fin: str) -> str | None:
    """
    Lee el archivo de transcripciones y lo analiza con Gemini.
    Guarda el análisis y retorna la ruta del archivo.
    """
    nombre_entrada = f"transcripciones_{categoria}_{fecha_inicio}_{fecha_fin}.txt"
    ruta_entrada = os.path.join(TMP_DIR, nombre_entrada)

    if not os.path.exists(ruta_entrada):
        print(f"  → [{categoria}] Archivo no encontrado: {ruta_entrada}")
        return None

    with open(ruta_entrada, "r", encoding="utf-8") as f:
        transcripciones = f.read()

    print(f"  → [{categoria}] Enviando a Gemini ({len(transcripciones)} caracteres)...")
    analisis = analizar_con_gemini(categoria, transcripciones)

    nombre_salida = f"analisis_{categoria}_{fecha_inicio}_{fecha_fin}.txt"
    ruta_salida = os.path.join(TMP_DIR, nombre_salida)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(analisis)

    print(f"  → [{categoria}] Análisis guardado: {ruta_salida}")
    return ruta_salida


def main():
    parser = argparse.ArgumentParser(description="Análisis con Gemini por categoría.")
    parser.add_argument("--inicio", required=True, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--fin", required=True, help="Fecha fin (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"[GEMINI] Analizando transcripciones: {args.inicio} → {args.fin}")

    for categoria in ["ventas", "soporte", "onboarding"]:
        print(f"\n[GEMINI] Procesando: {categoria.upper()}")
        procesar_categoria(categoria, args.inicio, args.fin)

    print("\n[GEMINI] ✅ Análisis completado.")


if __name__ == "__main__":
    main()
