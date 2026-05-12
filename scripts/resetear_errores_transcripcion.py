"""
scripts/resetear_errores_transcripcion.py
Resetea filas con Estado=error_transcripcion a Estado=pendiente
para que transcripcion.py pueda reintentarlas.

Uso:
  python scripts/resetear_errores_transcripcion.py
  python scripts/resetear_errores_transcripcion.py --inicio 2026-05-01 --fin 2026-05-31
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros, actualizar_registro

TABLAS = ["llamadas_ventas"]
DELAY = 0.3  # segundos entre PATCHes


def resetear(fecha_inicio: str = "", fecha_fin: str = "", dry_run: bool = False):
    total = 0
    for tabla in TABLAS:
        print(f"\n--- Tabla: {tabla} ---")
        registros = listar_registros(tabla, where="(Estado,eq,error_transcripcion)")
        print(f"  Encontrados: {len(registros)} con Estado=error_transcripcion")

        for r in registros:
            fecha = (r.get("Fecha") or "")[:10]
            if fecha_inicio and fecha < fecha_inicio:
                continue
            if fecha_fin and fecha > fecha_fin:
                continue

            nocodb_id = r.get("Id")
            call_id   = r.get("ID Fathom") or str(nocodb_id)
            print(f"  → [{call_id}] id={nocodb_id} fecha={fecha}  {'(DRY RUN)' if dry_run else 'reseteando...'}")

            if not dry_run:
                try:
                    actualizar_registro(tabla, nocodb_id, {"Estado": "pendiente"})
                    total += 1
                    time.sleep(DELAY)
                except Exception as e:
                    print(f"    [ERROR] {e}")

    print(f"\n✅ Reseteados: {total} registros → Estado=pendiente")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resetea error_transcripcion → pendiente.")
    parser.add_argument("--inicio", default="", help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--fin",    default="", help="Fecha fin   YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no modificar")
    args = parser.parse_args()
    resetear(fecha_inicio=args.inicio, fecha_fin=args.fin, dry_run=args.dry_run)
