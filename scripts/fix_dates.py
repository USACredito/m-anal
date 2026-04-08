import sys
from pprint import pprint
import time
from nocodb_client import *

def fix_dates():
    print("Obteniendo llamadas de ventas...")
    ventas = listar_registros("llamadas_ventas")
    
    # Mapear ID Llamada -> Fecha
    fecha_por_id = {}
    for v in ventas:
        call_id = v.get("ID Fathom")
        fecha = v.get("Fecha")
        if call_id and fecha:
            fecha_por_id[call_id] = fecha
    
    print(f"Mapeados {len(fecha_por_id)} IDs con fechas.")

    print("Obteniendo Setters...")
    setters = listar_registros("calificaciones_setters")
    for s in setters:
        call_id = s.get("ID Llamada")
        fecha = s.get("Fecha Llamada")
        if not fecha and call_id in fecha_por_id:
            row_id = s.get("Id")
            nueva_fecha = fecha_por_id[call_id]
            print(f"Parcheando Setter {row_id} con fecha {nueva_fecha}")
            actualizar_registro("calificaciones_setters", row_id, {"Fecha Llamada": nueva_fecha})

    print("Obteniendo Closers...")
    closers = listar_registros("calificaciones_closers")
    for c in closers:
        call_id = c.get("ID Llamada")
        fecha = c.get("Fecha Llamada")
        if not fecha and call_id in fecha_por_id:
            row_id = c.get("Id")
            nueva_fecha = fecha_por_id[call_id]
            print(f"Parcheando Closer {row_id} con fecha {nueva_fecha}")
            actualizar_registro("calificaciones_closers", row_id, {"Fecha Llamada": nueva_fecha})
            
    print("Fechas parcheadas.")

if __name__ == "__main__":
    fix_dates()
