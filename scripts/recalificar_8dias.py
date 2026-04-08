"""
scripts/recalificar_8dias.py
Recalifica TODAS las llamadas de los últimos 8 días que tienen transcripción,
sobrescribiendo calificaciones existentes con los nuevos campos (Puntos Fuertes,
Áreas de Mejora, Resumen).

Ejecutar desde el directorio raíz del proyecto:
    python scripts/recalificar_8dias.py

Flags opcionales:
    --dias N          Días hacia atrás (default: 8)
    --tipo setter     Solo recalificar setters
    --tipo closer     Solo recalificar closers
    --dry-run         Mostrar qué se procesaría sin guardar nada
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import crear_registro, actualizar_registro, listar_registros
from scripts.calificaciones import (
    llamar_openai_json,
    PROMPT_CALIDAD_SETTER,
    PROMPT_CALIDAD_CLOSER,
    PROMPT_CALIDAD_LEAD,
)

load_dotenv()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def cargar_calificaciones_existentes(tabla: str, campo_id: str) -> dict:
    """Retorna dict {id_llamada: nocodb_record_id} de calificaciones ya existentes."""
    print(f"  Cargando calificaciones existentes de '{tabla}'...")
    registros = listar_registros(tabla)
    mapa = {}
    for r in registros:
        call_id = str(r.get(campo_id) or r.get("ID Llamada") or "")
        noco_id = r.get("Id") or r.get("id")
        if call_id and noco_id:
            mapa[call_id] = int(noco_id)
    print(f"    → {len(mapa)} calificaciones encontradas.")
    return mapa


def guardar_o_actualizar(tabla: str, mapa_existentes: dict, campo_id_nombre: str,
                          call_id: str, payload: dict, dry_run: bool):
    """Crea o actualiza un registro según si ya existe."""
    if dry_run:
        accion = "ACTUALIZAR" if call_id in mapa_existentes else "CREAR"
        print(f"      [DRY-RUN] {accion} en '{tabla}' para llamada {call_id}")
        return

    if call_id in mapa_existentes:
        noco_id = mapa_existentes[call_id]
        actualizar_registro(tabla, noco_id, payload)
    else:
        crear_registro(tabla, payload)
        # Recargar el ID del nuevo registro (para futuras referencias en la misma sesión)
        # No es crítico para esta ejecución


# ─── PROCESO PRINCIPAL ────────────────────────────────────────────────────────

def procesar_llamada(r: dict, mapa_setters: dict, mapa_closers: dict,
                     mapa_leads: dict, dry_run: bool, filtro_tipo: str):
    call_id   = r.get("ID Fathom", "N/A")
    fecha     = r.get("Fecha", "")
    mes_anio  = fecha[:7] if fecha else datetime.now().strftime("%Y-%m")
    tipo      = (r.get("Tipo") or "").lower()
    participantes = r.get("Participantes", "")
    partes    = [p.strip() for p in participantes.split(",") if p.strip()]
    nombre_agente_meta = partes[0] if partes else "Desconocido"
    contexto  = f"\n\n[CONTEXTO]: El agente que realizó esta llamada se llama: {nombre_agente_meta}."
    transcripcion = r.get("Transcripción Texto", "")

    if not transcripcion:
        print(f"  [SKIP] {call_id}: sin transcripción.")
        return

    print(f"\n  Procesando {call_id}  |  tipo={tipo or 'desconocido'}  |  agente={nombre_agente_meta}")

    # ── Lead (siempre) ────────────────────────────────────────────────────────
    if not filtro_tipo or filtro_tipo == "todos":
        resultado_lead = llamar_openai_json(PROMPT_CALIDAD_LEAD, transcripcion)
        if "error" not in resultado_lead:
            payload_lead = {
                "ID Llamada": call_id,
                "Fecha Llamada": fecha,
                "Calificación": resultado_lead.get("calificacion", 0),
                "Nivel": resultado_lead.get("nivel", ""),
                "Justificación": resultado_lead.get("justificacion", ""),
                "Positivos": json.dumps(resultado_lead.get("factores_positivos", []), ensure_ascii=False),
                "Negativos": json.dumps(resultado_lead.get("factores_negativos", []), ensure_ascii=False),
                "Mes-Año": mes_anio,
            }
            guardar_o_actualizar("calificaciones_leads", mapa_leads,
                                 "ID Llamada", call_id, payload_lead, dry_run)
            if not dry_run:
                print(f"    [Lead] {resultado_lead.get('nivel','?')} | {resultado_lead.get('calificacion',0)}/10")
        else:
            print(f"    [Lead] ERROR: {resultado_lead.get('error')}")

    # ── Setter ────────────────────────────────────────────────────────────────
    if tipo == "setter" and filtro_tipo in ("setter", "todos", ""):
        resultado = llamar_openai_json(PROMPT_CALIDAD_SETTER, transcripcion + contexto)
        if "error" not in resultado:
            desglose = resultado.get("desglose", {})
            nombre = resultado.get("nombre_setter", nombre_agente_meta)
            if not nombre or nombre == "Desconocido":
                nombre = nombre_agente_meta
            payload = {
                "ID Llamada": call_id,
                "Setter": nombre,
                "Nota Total": float(resultado.get("calificacion_total", 0)),
                "Rapport": float(desglose.get("rapport", 0)),
                "Identificación Dolor": float(desglose.get("identificacion_dolor", 0)),
                "Venta Cita": float(desglose.get("venta_cita", 0)),
                "Objeciones": float(desglose.get("manejo_objeciones", 0)),
                "Agendó?": str(resultado.get("agendo_cita", "")),
                "Puntos Fuertes": json.dumps(resultado.get("puntos_fuertes", []), ensure_ascii=False),
                "Áreas de Mejora": json.dumps(resultado.get("areas_mejora", []), ensure_ascii=False),
                "Resumen": resultado.get("resumen_ejecutivo", ""),
                "Fecha Llamada": fecha,
                "Mes-Año": mes_anio,
            }
            guardar_o_actualizar("calificaciones_setters", mapa_setters,
                                 "ID Llamada", call_id, payload, dry_run)
            if not dry_run:
                print(f"    [Setter] {nombre} | {resultado.get('calificacion_total',0)}/10 | agenda={resultado.get('agendo_cita','?')}")
        else:
            print(f"    [Setter] ERROR: {resultado.get('error')}")

    # ── Closer ────────────────────────────────────────────────────────────────
    elif tipo == "closer" and filtro_tipo in ("closer", "todos", ""):
        resultado = llamar_openai_json(PROMPT_CALIDAD_CLOSER, transcripcion + contexto)
        if "error" not in resultado:
            desglose = resultado.get("desglose", {})
            nombre = resultado.get("nombre_closer", nombre_agente_meta)
            if not nombre or nombre == "Desconocido":
                nombre = nombre_agente_meta
            payload = {
                "ID Llamada": call_id,
                "Closer": nombre,
                "Nota Total": float(resultado.get("calificacion_total", 0)),
                "Rapport": float(desglose.get("rapport", 0)),
                "Descubrimiento": float(desglose.get("descubrimiento", 0)),
                "Presentación": float(desglose.get("presentacion", 0)),
                "Objeciones": float(desglose.get("objeciones", 0)),
                "Cierre": float(desglose.get("cierre", 0)),
                "Resultado": str(resultado.get("resultado_llamada", "")),
                "Puntos Fuertes": json.dumps(resultado.get("puntos_fuertes", []), ensure_ascii=False),
                "Áreas de Mejora": json.dumps(resultado.get("areas_mejora", []), ensure_ascii=False),
                "Resumen": resultado.get("resumen_ejecutivo", ""),
                "Fecha Llamada": fecha,
                "Mes-Año": mes_anio,
            }
            guardar_o_actualizar("calificaciones_closers", mapa_closers,
                                 "ID Llamada", call_id, payload, dry_run)
            if not dry_run:
                print(f"    [Closer] {nombre} | {resultado.get('calificacion_total',0)}/10 | resultado={resultado.get('resultado_llamada','?')}")
        else:
            print(f"    [Closer] ERROR: {resultado.get('error')}")

    elif tipo not in ("setter", "closer"):
        print(f"    [SKIP] Tipo '{tipo}' no reconocido como setter ni closer.")


def main():
    parser = argparse.ArgumentParser(description="Recalificar llamadas de los últimos N días.")
    parser.add_argument("--dias", type=int, default=8, help="Días hacia atrás (default: 8)")
    parser.add_argument("--tipo", choices=["setter", "closer", "todos"], default="todos",
                        help="Filtrar por tipo de llamada")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostrar qué se procesaría sin guardar nada")
    args = parser.parse_args()

    hoy = datetime.now()
    fecha_inicio = (hoy - timedelta(days=args.dias)).strftime("%Y-%m-%d")
    fecha_fin    = hoy.strftime("%Y-%m-%d")

    print(f"""
==============================================================
  RECALIFICACION MASIVA: {fecha_inicio} -> {fecha_fin}
  Tipo filtro: {args.tipo}
  Modo: {'DRY-RUN (no guarda nada)' if args.dry_run else 'PRODUCCION (guarda en NocoDB)'}
==============================================================
""")

    # Cargar llamadas con transcripción en el rango de fechas
    print("Cargando llamadas con transcripción...")
    todas = listar_registros("llamadas_ventas")
    llamadas = [
        r for r in todas
        if r.get("Transcripción Texto")
        and fecha_inicio <= (r.get("Fecha") or "") <= fecha_fin
        and (r.get("Duración (min)") or 0) >= 2
        and (args.tipo == "todos" or (r.get("Tipo") or "").lower() == args.tipo)
    ]

    if not llamadas:
        print(f"No hay llamadas con transcripción en los últimos {args.dias} días.")
        return

    setters_l = [r for r in llamadas if (r.get("Tipo") or "").lower() == "setter"]
    closers_l = [r for r in llamadas if (r.get("Tipo") or "").lower() == "closer"]
    otros_l   = [r for r in llamadas if (r.get("Tipo") or "").lower() not in ("setter", "closer")]

    print(f"Llamadas a procesar: {len(llamadas)} total")
    print(f"  Setters: {len(setters_l)}  |  Closers: {len(closers_l)}  |  Sin tipo: {len(otros_l)}")

    if otros_l:
        print(f"\n  AVISO: {len(otros_l)} llamadas sin tipo setter/closer seran omitidas.")
        print(f"  IDs: {[r.get('ID Fathom') for r in otros_l[:10]]}")

    # Cargar mapas de calificaciones existentes (para upsert)
    print("\nCargando calificaciones existentes para upsert...")
    mapa_setters = cargar_calificaciones_existentes("calificaciones_setters", "ID Llamada")
    mapa_closers = cargar_calificaciones_existentes("calificaciones_closers", "ID Llamada")
    mapa_leads   = cargar_calificaciones_existentes("calificaciones_leads",   "ID Llamada")

    # Confirmar si no es dry-run
    if not args.dry_run:
        print(f"\nSe van a recalificar {len(llamadas)} llamadas con OpenAI GPT-4o-mini.")
        print("Presiona Enter para continuar o Ctrl+C para cancelar...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nCancelado.")
            return

    # Procesar
    print(f"\nIniciando recalificación...\n{'='*60}")
    ok = 0
    errores = 0
    for i, r in enumerate(llamadas, 1):
        try:
            print(f"[{i}/{len(llamadas)}]", end="")
            procesar_llamada(r, mapa_setters, mapa_closers, mapa_leads,
                             args.dry_run, args.tipo if args.tipo != "todos" else "")
            ok += 1
        except Exception as e:
            print(f"  [ERROR inesperado] {r.get('ID Fathom')}: {e}")
            errores += 1

    print(f"""
==============================================================
  RECALIFICACION COMPLETADA
  Procesadas: {ok}  |  Errores: {errores}
==============================================================
""")


if __name__ == "__main__":
    main()
