"""
scripts/fix_tipo_llamadas.py
Corrige el campo Tipo en llamadas_ventas para todas las llamadas existentes,
usando la lista oficial de setters y closers en agentes_config.py.

Ejecutar UNA sola vez desde /app:
    python scripts/fix_tipo_llamadas.py

Flags:
    --dry-run   Mostrar cambios sin guardar nada
"""

import argparse
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros, actualizar_registro
from scripts.agentes_config import clasificar_llamada

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no guardar")
    args = parser.parse_args()

    print("Cargando todas las llamadas de llamadas_ventas...")
    todas = listar_registros("llamadas_ventas")
    print(f"Total: {len(todas)} llamadas\n")

    stats = {"setter": 0, "closer": 0, "ventas": 0, "sin_cambio": 0}
    cambios = []

    for r in todas:
        noco_id   = r.get("Id") or r.get("id")
        tipo_actual = (r.get("Tipo") or "").lower().strip()
        participantes = r.get("Participantes", "")
        partes = [p.strip() for p in participantes.split(",") if p.strip()]

        from_name = partes[0] if len(partes) > 0 else ""
        to_name   = partes[1] if len(partes) > 1 else ""

        tipo_nuevo = clasificar_llamada(from_name, to_name)

        if tipo_nuevo == tipo_actual:
            stats["sin_cambio"] += 1
            continue

        cambios.append((noco_id, r.get("ID Fathom", "?"), participantes, tipo_actual, tipo_nuevo))
        stats[tipo_nuevo] = stats.get(tipo_nuevo, 0) + 1

    print(f"Llamadas a actualizar : {len(cambios)}")
    print(f"  -> setter  : {stats['setter']}")
    print(f"  -> closer  : {stats['closer']}")
    print(f"  -> ventas  : {stats['ventas']}")
    print(f"  Sin cambio : {stats['sin_cambio']}\n")

    if not cambios:
        print("Nada que corregir.")
        return

    # Muestra preview de los primeros 20
    print("Preview (primeros 20):")
    for noco_id, call_id, partic, antes, despues in cambios[:20]:
        print(f"  {call_id[:20]:<22} {antes or '(vacío)':<12} -> {despues}  [{partic[:40]}]")
    if len(cambios) > 20:
        print(f"  ... y {len(cambios) - 20} más")

    if args.dry_run:
        print("\n[DRY-RUN] No se guardó nada.")
        return

    print(f"\nActualizando {len(cambios)} registros en NocoDB...")
    ok = 0
    errores = 0
    for i, (noco_id, call_id, _, _, tipo_nuevo) in enumerate(cambios, 1):
        try:
            actualizar_registro("llamadas_ventas", noco_id, {"Tipo": tipo_nuevo})
            ok += 1
            if i % 20 == 0:
                print(f"  {i}/{len(cambios)} actualizados...")
        except Exception as e:
            print(f"  [ERR] {call_id}: {e}")
            errores += 1

    print(f"\nCompletado: {ok} OK  |  {errores} errores")


if __name__ == "__main__":
    main()
