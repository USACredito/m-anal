"""
dashboard/app.py — Servidor Flask
Sirve el dashboard web y actúa como proxy seguro hacia NocoDB.
El token de NocoDB NUNCA se expone al frontend.

Ejecución:
    python dashboard/app.py

Acceso: http://localhost:5050
"""

import json
import os
import sys
from datetime import datetime, date

import requests as http_requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv

# Agregar raíz al path para importar nocodb_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import (
    crear_registro,
    actualizar_registro,
    listar_registros,
)
from scripts.agentes_config import es_setter_oficial, es_closer_oficial

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

app = Flask(__name__)
CORS(app)

PORT = 5050

# ─── DATOS DE DEMO (cuando NocoDB no está configurado) ────────────────────────

# Verificar si NocoDB tiene las credenciales mínimas para operar
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")
NOCODB_PROJECT_ID = os.getenv("NOCODB_PROJECT_ID", "")
NOCODB_CONFIGURED = bool(NOCODB_API_TOKEN and NOCODB_PROJECT_ID)

DEMO_AGENTES = [
    {"Id": 1, "nombre": "Carlos Méndez", "tipo": "closer", "email_fathom": "carlos@empresa.com", "activo": True, "fecha_registro": "2025-01-10"},
    {"Id": 2, "nombre": "Laura Gómez", "tipo": "closer", "email_fathom": "laura@empresa.com", "activo": True, "fecha_registro": "2025-01-15"},
    {"Id": 3, "nombre": "Miguel Torres", "tipo": "setter", "email_fathom": "miguel@empresa.com", "activo": True, "fecha_registro": "2025-02-01"},
    {"Id": 4, "nombre": "Ana Ruiz", "tipo": "setter", "email_fathom": "ana@empresa.com", "activo": True, "fecha_registro": "2025-02-10"},
]

DEMO_CALIFICACIONES_SETTERS = [
    {"nombre_setter": "Miguel Torres", "calificacion_total": 8.5, "rapport": 9, "identificacion_dolor": 8, "venta_cita": 9, "manejo_objeciones": 8, "resultado": "sí", "fecha_llamada": "2026-03-01", "mes_año": "2026-03"},
    {"nombre_setter": "Ana Ruiz", "calificacion_total": 7.0, "rapport": 7, "identificacion_dolor": 7, "venta_cita": 7, "manejo_objeciones": 7, "resultado": "no", "fecha_llamada": "2026-03-02", "mes_año": "2026-03"},
]

DEMO_CALIFICACIONES_CLOSERS = [
    {"nombre_closer": "Carlos Méndez", "calificacion_total": 9, "calificacion_rapport": 9, "calificacion_descubrimiento": 8, "calificacion_presentacion": 9, "calificacion_objeciones": 9, "calificacion_cierre": 10, "resultado": "vendió", "fecha_llamada": "2026-03-01", "mes_año": "2026-03"},
    {"nombre_closer": "Laura Gómez", "calificacion_total": 6, "calificacion_rapport": 6, "calificacion_descubrimiento": 5, "calificacion_presentacion": 7, "calificacion_objeciones": 5, "calificacion_cierre": 6, "resultado": "no vendió", "fecha_llamada": "2026-03-02", "mes_año": "2026-03"},
]

DEMO_CALIFICACIONES_ONBOARDING = [
    {"nombre_coach": "Pedro Salinas", "calificacion_total": 9, "calificacion_claridad": 9, "calificacion_adaptacion": 9, "calificacion_completitud": 9, "calificacion_tiempo": 8, "calificacion_satisfaccion": 10, "cliente_listo": "sí", "fecha_llamada": "2026-03-02", "mes_año": "2026-03"},
    {"nombre_coach": "Pedro Salinas", "calificacion_total": 8, "calificacion_claridad": 8, "calificacion_adaptacion": 9, "calificacion_completitud": 8, "calificacion_tiempo": 7, "calificacion_satisfaccion": 9, "cliente_listo": "sí", "fecha_llamada": "2026-03-06", "mes_año": "2026-03"},
    {"nombre_coach": "Sofía Vega", "calificacion_total": 5, "calificacion_claridad": 5, "calificacion_adaptacion": 4, "calificacion_completitud": 5, "calificacion_tiempo": 5, "calificacion_satisfaccion": 5, "cliente_listo": "parcialmente", "fecha_llamada": "2026-03-03", "mes_año": "2026-03"},
]

# Almacén en memoria para agentes (cuando NocoDB no está disponible)
_demo_agentes_store = [dict(a) for a in DEMO_AGENTES]
_demo_next_id = max(a["Id"] for a in _demo_agentes_store) + 1


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def semaforo(promedio: float | None) -> dict:
    """Retorna nivel, color y emoji del semáforo basado en el promedio."""
    if promedio is None:
        return {"nivel": "sin_datos", "color": "#64748b", "emoji": "⚪", "label": "Sin datos"}
    if promedio >= 8.0:
        return {"nivel": "excelente", "color": "#22c55e", "emoji": "🟢", "label": "Excelente"}
    if promedio >= 6.0:
        return {"nivel": "regular", "color": "#f59e0b", "emoji": "🟡", "label": "Regular"}
    return {"nivel": "critico", "color": "#ef4444", "emoji": "🔴", "label": "Crítico"}


def calcular_tendencia(calificaciones: list, campo: str = "calificacion_total") -> str:
    """Calcula si la tendencia es creciente, decreciente o estable (últimas 5)."""
    ultimas = [c.get(campo, 0) for c in calificaciones[-5:] if c.get(campo) is not None]
    if len(ultimas) < 2:
        return "estable"
    delta = ultimas[-1] - ultimas[0]
    if delta > 0.5:
        return "subiendo"
    if delta < -0.5:
        return "bajando"
    return "estable"


def get_calificaciones_por_nombre(tabla: str, campo_nombre: str, nombre: str) -> list:
    """Obtiene calificaciones de NocoDB filtrando por nombre (case-insensitive)."""
    try:
        todos = listar_registros(tabla)
        return [r for r in todos if str(r.get(campo_nombre, "")).strip().lower() == nombre.strip().lower()]
    except Exception:
        return []


def get_calificaciones_demo(tipo: str, nombre: str) -> list:
    """Retorna calificaciones del store de demo."""
    if tipo == "closer":
        return [c for c in DEMO_CALIFICACIONES_CLOSERS
                if c["nombre_closer"].lower() == nombre.lower()]
    if tipo == "setter":
        return [c for c in DEMO_CALIFICACIONES_SETTERS
                if c["nombre_setter"].lower() == nombre.lower()]
    return []


def metricas_agente(agente: dict) -> dict:
    """Calcula las métricas completas de un agente."""
    # NocoDB v3 devuelve los campos con el Título (mayúsculas)
    nombre = agente.get("Nombre") or agente.get("nombre", "")
    tipo   = (agente.get("Tipo")   or agente.get("tipo",   "")).lower()

    if NOCODB_CONFIGURED:
        if tipo == "closer":
            calificaciones = get_calificaciones_por_nombre(
                "calificaciones_closers", "Closer", nombre
            )
            campo_total = "Nota Total"
            dims = ["Rapport", "Descubrimiento", "Presentación", "Objeciones", "Cierre"]
        elif tipo == "setter":
            calificaciones = get_calificaciones_por_nombre(
                "calificaciones_setters", "Setter", nombre
            )
            campo_total = "Nota Total"
            dims = ["Rapport", "Identificación Dolor", "Venta Cita", "Objeciones"]
        else:
            calificaciones = []
            campo_total = "Nota Total"
            dims = []
    else:
        calificaciones = get_calificaciones_demo(tipo, nombre)
        campo_total = "calificacion_total"
        if tipo == "closer":
            dims = ["calificacion_rapport", "calificacion_descubrimiento", "calificacion_presentacion", "calificacion_objeciones", "calificacion_cierre"]
        elif tipo == "setter":
            dims = ["rapport", "identificacion_dolor", "venta_cita", "manejo_objeciones"]
        else:
            dims = []

    if not calificaciones:
        return {
            "total_llamadas": 0,
            "promedio": None,
            "semaforo": semaforo(None),
            "tendencia": "estable",
            "mejor": None,
            "peor": None,
            "desglose": {},
            "historial": [],
        }

    valores = [float(c.get(campo_total, 0) or 0) for c in calificaciones]
    promedio = round(sum(valores) / len(valores), 1)

    # Desglose promedio por dimensión
    desglose = {}
    for dim in dims:
        vals = [float(c.get(dim, 0) or 0) for c in calificaciones if c.get(dim) is not None]
        label = dim.replace("calificacion_", "").replace("_", " ").title()
        desglose[label] = round(sum(vals) / len(vals), 1) if vals else 0

    # Historial para gráfica
    historial = [
        {"fecha": c.get("Fecha Llamada", ""), "calificacion": float(c.get(campo_total, 0) or 0)}
        for c in calificaciones[-10:]
    ]

    return {
        "total_llamadas": len(calificaciones),
        "promedio": promedio,
        "semaforo": semaforo(promedio),
        "tendencia": calcular_tendencia(calificaciones, campo_total),
        "mejor": max(valores),
        "peor": min(valores),
        "desglose": desglose,
        "historial": historial,
    }


# ─── RUTAS API ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/agentes", methods=["GET"])
def api_get_agentes():
    if NOCODB_CONFIGURED:
        try:
            print(f"[DASHBOARD] Buscando agentes en NocoDB...")
            agentes = listar_registros("agentes")
            print(f"[DASHBOARD] Se encontraron {len(agentes)} agentes.")
            if not agentes:
                print("[DASHBOARD] AVISO: La tabla de agentes en NocoDB está vacía o el Table ID es incorrecto.")
            return jsonify({"demo": False, "datos": agentes})
        except Exception as e:
            print(f"[DASHBOARD] Fallo al conectar con NocoDB: {e}")
            return jsonify({"error": str(e), "demo": True, "datos": _demo_agentes_store})
    return jsonify({"demo": True, "datos": _demo_agentes_store})


@app.route("/api/agentes", methods=["POST"])
def api_crear_agente():
    global _demo_next_id
    data = request.json
    nuevo = {
        "nombre": data.get("nombre", ""),
        "tipo": data.get("tipo", "closer"),
        "email_fathom": data.get("email_fathom", ""),
        "activo": data.get("activo", True),
        "fecha_registro": date.today().isoformat(),
    }

    if NOCODB_CONFIGURED:
        try:
            resultado = crear_registro("agentes", nuevo)
            return jsonify(resultado), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    nuevo["Id"] = _demo_next_id
    _demo_next_id += 1
    _demo_agentes_store.append(nuevo)
    return jsonify({"demo": True, "datos": nuevo}), 201


@app.route("/api/agentes/<int:agente_id>", methods=["PUT"])
def api_actualizar_agente(agente_id):
    data = request.json

    if NOCODB_CONFIGURED:
        try:
            resultado = actualizar_registro("agentes", agente_id, data)
            return jsonify(resultado)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    for a in _demo_agentes_store:
        if a["Id"] == agente_id:
            a.update(data)
            return jsonify({"demo": True, "datos": a})
    return jsonify({"error": "no encontrado"}), 404


@app.route("/api/agentes/<int:agente_id>", methods=["DELETE"])
def api_eliminar_agente(agente_id):
    if NOCODB_CONFIGURED:
        try:
            resultado = actualizar_registro("agentes", agente_id, {"activo": False})
            return jsonify(resultado)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    for a in _demo_agentes_store:
        if a["Id"] == agente_id:
            a["activo"] = False
            return jsonify({"demo": True, "ok": True})
    return jsonify({"error": "no encontrado"}), 404


@app.route("/api/metricas", methods=["GET"])
def api_metricas():
    """Retorna métricas consolidadas con semáforo para todos los agentes activos.
    Lee directamente de las tablas de calificaciones v3 (no depende de tabla agentes vacía).
    """
    resultado = []

    if NOCODB_CONFIGURED:
        try:
            # ── Closers ──────────────────────────────────────────────────────
            todas_closers = listar_registros("calificaciones_closers")
            # Agrupar por nombre del Closer
            closers_map = {}
            for r in todas_closers:
                nombre = r.get("Closer") or r.get("nombre_closer", "Desconocido")
                if not es_closer_oficial(nombre):
                    continue
                if nombre not in closers_map:
                    closers_map[nombre] = []
                closers_map[nombre].append(r)

            for nombre, calificaciones in closers_map.items():
                campo_total = "Nota Total"
                dims = ["Rapport", "Descubrimiento", "Presentación", "Objeciones", "Cierre"]
                valores = [float(c.get(campo_total) or 0) for c in calificaciones]
                promedio = round(sum(valores) / len(valores), 1) if valores else None
                desglose = {}
                for dim in dims:
                    vals = [float(c.get(dim) or 0) for c in calificaciones if c.get(dim) is not None]
                    desglose[dim] = round(sum(vals)/len(vals), 1) if vals else 0
                historial = [
                    {"fecha": c.get("Fecha Llamada", ""), "calificacion": float(c.get(campo_total) or 0)}
                    for c in calificaciones[-10:]
                ]
                resultado.append({
                    "id": nombre,
                    "nombre": nombre,
                    "tipo": "closer",
                    "activo": True,
                    "total_llamadas": len(calificaciones),
                    "promedio": promedio,
                    "semaforo": semaforo(promedio),
                    "tendencia": calcular_tendencia(calificaciones, campo_total),
                    "mejor": max(valores) if valores else None,
                    "peor": min(valores) if valores else None,
                    "desglose": desglose,
                    "historial": historial,
                    "tasa_cierre": round(
                        sum(1 for c in calificaciones
                            if str(c.get("Resultado") or "").lower() in ("vendió", "vendo", "cerrado", "venta", "sí", "si"))
                        / len(calificaciones) * 100, 1
                    ) if calificaciones else 0,
                })

            # ── Setters ──────────────────────────────────────────────────────
            todas_setters = listar_registros("calificaciones_setters")
            setters_map = {}
            for r in todas_setters:
                nombre = r.get("Setter") or r.get("nombre_setter", "Desconocido")
                if not es_setter_oficial(nombre):
                    continue
                if nombre not in setters_map:
                    setters_map[nombre] = []
                setters_map[nombre].append(r)

            for nombre, calificaciones in setters_map.items():
                campo_total = "Nota Total"
                dims = ["Rapport", "Identificación Dolor", "Venta Cita", "Objeciones"]
                valores = [float(c.get(campo_total) or 0) for c in calificaciones]
                promedio = round(sum(valores) / len(valores), 1) if valores else None
                desglose = {}
                for dim in dims:
                    vals = [float(c.get(dim) or 0) for c in calificaciones if c.get(dim) is not None]
                    desglose[dim] = round(sum(vals)/len(vals), 1) if vals else 0
                historial = [
                    {"fecha": c.get("Fecha Llamada", ""), "calificacion": float(c.get(campo_total) or 0)}
                    for c in calificaciones[-10:]
                ]
                resultado.append({
                    "id": nombre,
                    "nombre": nombre,
                    "tipo": "setter",
                    "activo": True,
                    "total_llamadas": len(calificaciones),
                    "promedio": promedio,
                    "semaforo": semaforo(promedio),
                    "tendencia": calcular_tendencia(calificaciones, campo_total),
                    "mejor": max(valores) if valores else None,
                    "peor": min(valores) if valores else None,
                    "desglose": desglose,
                    "historial": historial,
                    "tasa_agendamiento": round(
                        sum(1 for s in calificaciones
                            if str(s.get("Agendó?") or "").strip().lower() in ("sí", "si", "yes", "1", "true"))
                        / len(calificaciones) * 100, 1
                    ) if calificaciones else 0,
                })

        except Exception as e:
            print(f"[DASHBOARD] Error leyendo calificaciones: {e}")
            # Fallback a demo
            resultado = _build_demo_metricas()
    else:
        resultado = _build_demo_metricas()

    # Ordenar: críticos primero
    orden = {"critico": 0, "regular": 1, "excelente": 2, "sin_datos": 3}
    resultado.sort(key=lambda x: orden.get(x["semaforo"]["nivel"], 99))

    return jsonify({"demo": not NOCODB_CONFIGURED, "datos": resultado})


def _build_demo_metricas():
    """Genera métricas de demo cuando NocoDB no está disponible."""
    out = []
    for agente in _demo_agentes_store:
        if not agente["activo"]:
            continue
        m = metricas_agente(agente)
        out.append({
            "id": agente["Id"],
            "nombre": agente["nombre"],
            "tipo": agente["tipo"],
            "activo": True,
            **m,
        })
    return out



@app.route("/api/llamadas", methods=["GET"])
def api_llamadas():
    """Retorna calificaciones individuales de closers y setters para la vista de llamadas."""
    if not NOCODB_CONFIGURED:
        return jsonify({"demo": True, "datos": {
            "closers": DEMO_CALIFICACIONES_CLOSERS,
            "setters": DEMO_CALIFICACIONES_SETTERS
        }})
    try:
        closers = listar_registros("calificaciones_closers")
        setters = listar_registros("calificaciones_setters")
        return jsonify({"demo": False, "datos": {"closers": closers, "setters": setters}})
    except Exception as e:
        print(f"[DASHBOARD] Error leyendo llamadas: {e}")
        return jsonify({"error": str(e), "datos": {"closers": [], "setters": []}}), 500


@app.route("/api/resumen_mensual", methods=["GET"])
def api_resumen_mensual():
    """Retorna el historial mensual de promedios para gráficas de evolución."""
    if NOCODB_CONFIGURED:
        try:
            datos = listar_registros("resumen_mensual_calidad")
            return jsonify(datos)
        except Exception:
            pass

    # Demo: últimos 6 meses
    demo = [
        {"mes_año": "2025-10", "promedio_calidad_leads": 6.5, "promedio_calidad_closers": 6.8, "promedio_calidad_setters": 6.0},
        {"mes_año": "2025-11", "promedio_calidad_leads": 6.8, "promedio_calidad_closers": 7.0, "promedio_calidad_setters": 6.5},
        {"mes_año": "2025-12", "promedio_calidad_leads": 7.0, "promedio_calidad_closers": 7.3, "promedio_calidad_setters": 7.0},
        {"mes_año": "2026-01", "promedio_calidad_leads": 7.2, "promedio_calidad_closers": 7.5, "promedio_calidad_setters": 7.5},
        {"mes_año": "2026-02", "promedio_calidad_leads": 7.8, "promedio_calidad_closers": 7.9, "promedio_calidad_setters": 8.0},
        {"mes_año": "2026-03", "promedio_calidad_leads": 8.0, "promedio_calidad_closers": 8.2, "promedio_calidad_setters": 8.3},
    ]
    return jsonify({"demo": True, "datos": demo})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Endpoint de chat con el agente IA.
    Recibe una pregunta, obtiene contexto de NocoDB y responde con GPT-4o-mini.
    Body JSON: { "mensaje": "...", "contexto": "setter|closer|todos", "limite": 300 }
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY no configurada"}), 500

    data = request.json or {}
    mensaje = (data.get("mensaje") or "").strip()
    contexto_tipo = (data.get("contexto") or "todos").lower()
    limite = min(int(data.get("limite") or 300), 500)

    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    # ── Recopilar datos de NocoDB para darle contexto al agente ──
    datos_contexto = ""
    try:
        if NOCODB_CONFIGURED:
            if contexto_tipo in ("setter", "todos"):
                setters = listar_registros("calificaciones_setters")[-limite:]
                if setters:
                    resumen_setters = []
                    for s in setters:
                        item = {
                            "setter": s.get("Setter", ""),
                            "nota": s.get("Nota Total", 0),
                            "agendo": s.get("Agendó?", ""),
                            "fecha": s.get("Fecha Llamada", ""),
                            "rapport": s.get("Rapport", 0),
                            "dolor": s.get("Identificación Dolor", 0),
                            "venta_cita": s.get("Venta Cita", 0),
                            "objeciones": s.get("Objeciones", 0),
                            "puntos_fuertes": s.get("Puntos Fuertes", ""),
                            "areas_mejora": s.get("Áreas de Mejora", ""),
                            "resumen": s.get("Resumen", ""),
                        }
                        resumen_setters.append(item)
                    datos_contexto += f"\n\n=== CALIFICACIONES SETTERS (últimas {len(resumen_setters)}) ===\n"
                    datos_contexto += json.dumps(resumen_setters, ensure_ascii=False, indent=None)

            if contexto_tipo in ("closer", "todos"):
                closers = listar_registros("calificaciones_closers")[-limite:]
                if closers:
                    resumen_closers = []
                    for c in closers:
                        item = {
                            "closer": c.get("Closer", ""),
                            "nota": c.get("Nota Total", 0),
                            "resultado": c.get("Resultado", ""),
                            "fecha": c.get("Fecha Llamada", ""),
                            "rapport": c.get("Rapport", 0),
                            "descubrimiento": c.get("Descubrimiento", 0),
                            "presentacion": c.get("Presentación", 0),
                            "objeciones": c.get("Objeciones", 0),
                            "cierre": c.get("Cierre", 0),
                            "puntos_fuertes": c.get("Puntos Fuertes", ""),
                            "areas_mejora": c.get("Áreas de Mejora", ""),
                            "resumen": c.get("Resumen", ""),
                        }
                        resumen_closers.append(item)
                    datos_contexto += f"\n\n=== CALIFICACIONES CLOSERS (últimas {len(resumen_closers)}) ===\n"
                    datos_contexto += json.dumps(resumen_closers, ensure_ascii=False, indent=None)

            # Leads
            leads = listar_registros("calificaciones_leads")[-limite:]
            if leads:
                resumen_leads = []
                for l in leads:
                    resumen_leads.append({
                        "calificacion": l.get("Calificación", 0),
                        "nivel": l.get("Nivel", ""),
                        "justificacion": l.get("Justificación", ""),
                        "positivos": l.get("Positivos", ""),
                        "negativos": l.get("Negativos", ""),
                        "fecha": l.get("Fecha Llamada", ""),
                    })
                datos_contexto += f"\n\n=== CALIDAD DE LEADS (últimas {len(resumen_leads)}) ===\n"
                datos_contexto += json.dumps(resumen_leads, ensure_ascii=False, indent=None)

    except Exception as e:
        print(f"[CHAT] Error obteniendo contexto de NocoDB: {e}")
        datos_contexto = "(No se pudo obtener datos de NocoDB)"

    hoy = datetime.now().strftime("%Y-%m-%d")

    system_prompt = f"""Eres el Analista IA del equipo de ventas. Tienes acceso a los datos reales de calificaciones de llamadas de venta.

Fecha de hoy: {hoy}

Tu rol es responder preguntas estratégicas del equipo de marketing y management basándote exclusivamente en los datos proporcionados. Puedes:
- Identificar patrones en preguntas/objeciones frecuentes (Q&A)
- Analizar qué dudas o objeciones se repiten más
- Comparar desempeño entre setters o closers
- Detectar tendencias por período
- Sugerir mejoras de contenido de captación
- Generar resúmenes estructurados por agente o período

Responde en español, de forma clara y estructurada. Si la pregunta requiere datos que no están disponibles, indícalo.

DATOS DISPONIBLES:
{datos_contexto if datos_contexto else "No hay datos cargados actualmente."}
"""

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensaje}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        resp = http_requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        respuesta = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"respuesta": respuesta, "ok": True})

    except Exception as e:
        print(f"[CHAT] Error al llamar a OpenAI: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    modo = "DEMO (NocoDB no configurado)" if not NOCODB_CONFIGURED else "PRODUCCIÓN"
    print(f"""
╔══════════════════════════════════════════════════════╗
║     DASHBOARD DE ANÁLISIS DE LLAMADAS               ║
╠══════════════════════════════════════════════════════╣
║  Modo:   {modo:<41}║
║  URL:    http://localhost:{PORT:<27}║
╚══════════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=PORT, debug=False)
