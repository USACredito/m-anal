import sys
sys.path.append(".")
from scripts.nocodb_client import listar_registros

try:
    print("Testing GET...")
    data = listar_registros("llamadas_ventas", limit=5)
    print("GET OK. Items:", len(data))
    if data:
        print("Sample item:", data[0])
except Exception as e:
    import traceback
    traceback.print_exc()

