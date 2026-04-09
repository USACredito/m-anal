"""
scripts/limpiar_wireless_caller.py
Elimina todos los registros de calificaciones_closers y calificaciones_setters
donde el nombre del agente es "WIRELESS CALLER" (o cualquier variante).

Uso:
    python scripts/limpiar_wireless_caller.py
    python scripts/limpiar_wireless_caller.py --dry-run
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros, borrar_registros


def limpiar(tabla: str, campo_agente: str, dry_run: bool):
    print(f"\n[{tabla}] Cargando registros...")
    registros = listar_registros(tabla)
    ids_wc = [
        r["Id"] for r in registros
        if "wireless" in (r.get(campo_agente) or "").lower()
    ]
    if not ids_wc:
        print(f"  → Ningún WIRELESS CALLER encontrado. OK.")
        return

    print(f"  → {len(ids_wc)} registros WIRELESS CALLER encontrados.")
    if dry_run:
        for r in registros:
            if "wireless" in (r.get(campo_agente) or "").lower():
                print(f"    [DRY-RUN] Id={r['Id']} | {campo_agente}={r.get(campo_agente)} | Fecha={r.get('Fecha Llamada')}")
        return

    status = borrar_registros(tabla, ids_wc)
    print(f"  → Borrados {len(ids_wc)} registros (HTTP {status}).")


def main():
    parser = argparse.ArgumentParser(description="Eliminar registros WIRELESS CALLER de calificaciones.")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se borraría, sin borrar nada.")
    args = parser.parse_args()

    modo = "DRY-RUN" if args.dry_run else "PRODUCCION"
    print(f"=== Limpieza WIRELESS CALLER [{modo}] ===")

    limpiar("calificaciones_closers", "Closer", args.dry_run)
    limpiar("calificaciones_setters", "Setter", args.dry_run)

    print("\n=== Listo. ===")


if __name__ == "__main__":
    main()
