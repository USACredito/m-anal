import sys
import os
import requests
from nocodb_client import *

def clean_short_calls():
    print("Buscando llamadas cortas (< 2 min) en NocoDB...")
    todas = listar_registros("llamadas_ventas")
    
    a_borrar = []
    for c in todas:
        duracion = c.get("Duración (min)") or c.get("Duración", 0)
        try:
            duracion = float(duracion or 0)
        except:
            duracion = 0
            
        if duracion < 2:
            a_borrar.append(c.get("Id"))
            
    if not a_borrar:
        print("No hay llamadas cortas que borrar.")
        return
        
    print(f"Encontradas {len(a_borrar)} llamadas de menos de 2 minutos. Borrando...")
    
    # NocoDB v3 bulk delete
    # Usamos NocoDB API v3 /api/v3/data/{PROJECT_ID}/{id} si eliminamos uno a uno,
    # o busquemos cómo eliminar.
    
    headers = {
        "xc-token": NOCODB_API_TOKEN,
        "Content-Type": "application/json" # Para DELETE it's recommended
    }
    
    exitos = 0
    url = f"{RAW_URL}/api/v3/data/{PROJECT_ID}/{MAPA_TABLAS['llamadas_ventas']}"
    
    # Payload para delete bulk ([{ "Id": 1 }])
    payload_borrar = [{"Id": r_id} for r_id in a_borrar]
    
    # Vemos si soporta bulk
    try:
        resp = requests.delete(url, headers=headers, json=payload_borrar)
        if resp.status_code == 200:
            print(f"Borradas las llamadas exitosamente (bulk).")
        else:
            print(f"Fallo en bulk, borrando una por una...")
            for r_id in a_borrar:
                url_single = f"{url}/{r_id}"
                r = requests.delete(url_single, headers=headers)
                if r.status_code == 200:
                    exitos += 1
            print(f"Borradas {exitos}/{len(a_borrar)} llamadas individualmente.")
    except Exception as e:
        print(f"Error borrando: {e}")

if __name__ == "__main__":
    clean_short_calls()

