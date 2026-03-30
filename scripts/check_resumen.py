import sys
sys.path.append(".")
from scripts.nocodb_client import listar_registros

try:
    print("Obteniendo Resumen Mensual...")
    data = listar_registros("resumen_mensual_calidad")
    print(f"Total registros: {len(data)}")
    for d in data:
        print(d)
except Exception as e:
    import traceback
    traceback.print_exc()
