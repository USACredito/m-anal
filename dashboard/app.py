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
    {"Id": 3, "nombre": "Miguel Torres", "tipo": "soporte", "email_fathom": "miguel@empresa.com", "activo": True, "fecha_registro": "2025-02-01"},
    {"Id": 4, "nombre": "Ana Ruiz", "tipo": "soporte", "email_fathom": "ana@empresa.com", "activo": True, "fecha_registro": "2025-02-10"},
    {"Id": 5, "nombre": "Pedro Salinas", "tipo": "onboarding", "email_fathom": "pedro@empresa.com", "activo": True, "fecha_registro": "2025-01-20"},
    {"Id": 6, "nombre": "Sofía Vega", "tipo": "onboarding", "email_fathom": "sofia@empresa.com", "activo": False, "fecha_registro": "2025-03-01"},
]

DEMO_CALIFICACIONES_CLOSERS = [
    {"nombre_closer": "Carlos Méndez", "calificacion_total": 9, "calificacion_rapport": 9, "calificacion_descubrimiento": 8, "calificacion_presentacion": 9, "calificacion_objeciones": 9, "calificacion_cierre": 10, "resultado": "vendió", "fecha_llamada": "2026-03-01", "mes_año": "2026-03"},
    {"nombre_closer": "Carlos Méndez", "calificacion_total": 8, "calificacion_rapport": 8, "calificacion_descubrimiento": 9, "calificacion_presentacion": 8, "calificacion_objeciones": 7, "calificacion_cierre": 8, "resultado": "vendió", "fecha_llamada": "2026-03-05", "mes_año": "2026-03"},
    {"nombre_closer": "Carlos Méndez", "calificacion_total": 9, "calificacion_rapport": 10, "calificacion_descubrimiento": 9, "calificacion_presentacion": 9, "calificacion_objeciones": 8, "calificacion_cierre": 9, "resultado": "vendió", "fecha_llamada": "2026-03-07", "mes_año": "2026-03"},
    {"nombre_closer": "Laura Gómez", "calificacion_total": 6, "calificacion_rapport": 6, "calificacion_descubrimiento": 5, "calificacion_presentacion": 7, "calificacion_objeciones": 5, "calificacion_cierre": 6, "resultado": "no vendió", "fecha_llamada": "2026-03-02", "mes_año": "2026-03"},
    {"nombre_closer": "Laura Gómez", "calificacion_total": 5, "calificacion_rapport": 6, "calificacion_descubrimiento": 4, "calificacion_presentacion": 5, "calificacion_objeciones": 4, "calificacion_cierre": 5, "resultado": "no vendió", "fecha_llamada": "2026-03-06", "mes_año": "2026-03"},
    {"nombre_closer": "Laura Gómez", "calificacion_total": 4, "calificacion_rapport": 5, "calificacion_descubrimiento": 3, "calificacion_presentacion": 4, "calificacion_objeciones": 4, "calificacion_cierre": 3, "resultado": "no vendió", "fecha_llamada": "2026-03-08", "mes_año": "2026-03"},
    {"nombre_closer": "Miguel Torres", "calificacion_total": 7, "calificacion_rapport": 7, "calificacion_descubrimiento": 7, "calificacion_presentacion": 7, "calificacion_objeciones": 7, "calificacion_cierre": 7, "resultado": "seguimiento pendiente", "fecha_llamada": "2026-03-03", "mes_año": "2026-03"},
    {"nombre_closer": "Ana Ruiz", "calificacion_total": 8, "calificacion_rapport": 8, "calificacion_descubrimiento": 8, "calificacion_presentacion": 9, "calificacion_objeciones": 8, "calificacion_cierre": 8, "resultado": "vendió", "fecha_llamada": "2026-03-04", "mes_año": "2026-03"},
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
    if tipo in ("closer", "soporte"):
        return [c for c in DEMO_CALIFICACIONES_CLOSERS
                if c["nombre_closer"].lower() == nombre.lower()]
    if tipo == "onboarding":
        return [c for c in DEMO_CALIFICACIONES_ONBOARDING
                if c["nombre_coach"].lower() == nombre.lower()]
    return []


def metricas_agente(agente: dict) -> dict:
    """Calcula las métricas completas de un agente."""
    nombre = agente["nombre"]
    tipo = agente["tipo"]

    if NOCODB_CONFIGURED:
        if tipo in ("closer", "soporte"):
            calificaciones = get_calificaciones_por_nombre(
                "calificaciones_closers", "Closer", nombre
            )
            campo_total = "Nota Total"
        elif tipo == "setter":
            calificaciones = get_calificaciones_por_nombre(
                "calificaciones_leads", "ID Llamada", "" # Para leads, buscamos todos los registros por ahora o por ID
            )
            # Para Setters/Leads, no buscamos por nombre exacto porque el prompt actual no extrae 'nombre_setter'
            # pero podemos mostrar el promedio global de la tabla.
            campo_total = "Calificación"
        else:
            calificaciones = get_calificaciones_por_nombre(
                "calificaciones_onboarding", "Coach", nombre
            )
            campo_total = "Nota Total"
    else:
        calificaciones = get_calificaciones_demo(tipo, nombre)
        campo_total = "calificacion_total"

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

    valores = [c.get(campo_total, 0) for c in calificaciones]
    promedio = round(sum(valores) / len(valores), 1)

    # Desglose promedio por dimensión
    desglose = {}
    if tipo == "closer" or tipo == "soporte":
        dims = ["Rapport", "Descubrimiento",
                "Presentación", "Objeciones", "Cierre"]
        labels = ["Rapport", "Descubrimiento", "Presentación", "Objeciones", "Cierre"]
    else:
        dims = ["Claridad", "Adaptación",
                "Completitud", "Tiempo", "Satisfacción"]
        labels = ["Claridad", "Adaptación", "Completitud", "Tiempo", "Satisfacción"]

    for dim, label in zip(dims, labels):
        vals = [c.get(dim, 0) for c in calificaciones if c.get(dim) is not None]
        desglose[label] = round(sum(vals) / len(vals), 1) if vals else 0

    # Historial para gráfica
    historial = [
        {"fecha": c.get("Fecha Llamada", ""), "calificacion": c.get(campo_total, 0)}
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
    """Retorna métricas consolidadas con semáforo para todos los agentes activos."""
    if NOCODB_CONFIGURED:
        try:
            agentes = listar_registros("agentes", where="(activo,eq,true)")
        except Exception:
            agentes = [a for a in _demo_agentes_store if a["activo"]]
    else:
        agentes = [a for a in _demo_agentes_store if a["activo"]]

    resultado = []
    for agente in agentes:
        m = metricas_agente(agente)
        resultado.append({
            "id": agente.get("Id"),
            "nombre": agente.get("nombre"),
            "tipo": agente.get("tipo"),
            "activo": agente.get("activo"),
            **m,
        })

    # Ordenar: críticos primero, luego regular, luego excelente
    orden = {"critico": 0, "regular": 1, "excelente": 2, "sin_datos": 3}
    resultado.sort(key=lambda x: orden.get(x["semaforo"]["nivel"], 99))

    return jsonify({"demo": not NOCODB_CONFIGURED, "datos": resultado})


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
        {"mes_año": "2025-10", "promedio_calidad_leads": 6.5, "promedio_calidad_closers": 6.8, "promedio_calidad_onboarding": 7.0},
        {"mes_año": "2025-11", "promedio_calidad_leads": 6.8, "promedio_calidad_closers": 7.0, "promedio_calidad_onboarding": 7.2},
        {"mes_año": "2025-12", "promedio_calidad_leads": 7.0, "promedio_calidad_closers": 7.3, "promedio_calidad_onboarding": 7.5},
        {"mes_año": "2026-01", "promedio_calidad_leads": 7.2, "promedio_calidad_closers": 7.5, "promedio_calidad_onboarding": 7.8},
        {"mes_año": "2026-02", "promedio_calidad_leads": 7.8, "promedio_calidad_closers": 7.9, "promedio_calidad_onboarding": 8.1},
        {"mes_año": "2026-03", "promedio_calidad_leads": 8.0, "promedio_calidad_closers": 8.2, "promedio_calidad_onboarding": 8.5},
    ]
    return jsonify({"demo": True, "datos": demo})


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
