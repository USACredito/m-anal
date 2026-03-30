import sys
sys.path.append(".")
import os
import requests
from dotenv import load_dotenv
from scripts.nocodb_client import _get_table_url, HEADERS, listar_registros

load_dotenv()
try:
    print("Obteniendo agentes actuales...")
    data = listar_registros("agentes")
    print("Agentes actuales:", len(data))
    for d in data:
        print(d)
        
    print("\nEstructura intentada para un nuevo agente...")
except Exception as e:
    import traceback
    traceback.print_exc()
