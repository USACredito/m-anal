"""
fix_desconocidos.py
Busca registros con nombre "Desconocido" en calificaciones_closers y calificaciones_setters,
luego los corrige usando el nombre real guardado en v3_llamadas_ventas (campo Participantes).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from scripts.nocodb_client import listar_registros, actualizar_registro

def corregir_desconocidos():
    print("=== CORRIGIENDO REGISTROS 'Desconocido' ===\n")

    # 1. Cargar todas las llamadas ventas (para buscar el nombre por ID)
    print("Cargando llamadas ventas...")
    llamadas = listar_registros("llamadas_ventas")
    # Crear mapa ID Fathom → primer participante (nombre del agente)
    mapa_nombres = {}
    for ll in llamadas:
        fid = ll.get("ID Fathom") or ll.get("id_fathom") or ll.get("ID Llamada")
        participantes = ll.get("Participantes", "")
        if fid and participantes:
            partes = [p.strip() for p in participantes.split(",") if p.strip()]
            if partes:
                mapa_nombres[str(fid)] = partes[0]
    print(f"  → {len(mapa_nombres)} llamadas indexadas.\n")

    # 2. Corregir calificaciones_closers
    print("Revisando Calificaciones Closers...")
    closers = listar_registros("calificaciones_closers")
    closers_corregidos = 0
    for c in closers:
        nombre_actual = c.get("Closer") or c.get("nombre_closer", "")
        if nombre_actual.strip().lower() in ("desconocido", "", "none"):
            call_id = str(c.get("ID Llamada") or c.get("id_fathom") or "")
            nombre_correcto = mapa_nombres.get(call_id)
            if nombre_correcto and nombre_correcto.lower() != "desconocido":
                record_id = c.get("Id") or c.get("id")
                try:
                    actualizar_registro("calificaciones_closers", record_id, {"Closer": nombre_correcto})
                    print(f"  ✅ Closer ID {record_id}: 'Desconocido' → '{nombre_correcto}'")
                    closers_corregidos += 1
                except Exception as e:
                    print(f"  ⚠️  Error actualizando closer ID {record_id}: {e}")
            else:
                print(f"  ℹ️  Closer ID {c.get('Id')}: no se encontró nombre para call_id={call_id}")
    print(f"  → {closers_corregidos} closers corregidos.\n")

    # 3. Corregir calificaciones_setters
    print("Revisando Calificaciones Setters...")
    setters = listar_registros("calificaciones_setters")
    setters_corregidos = 0
    for s in setters:
        nombre_actual = s.get("Setter") or s.get("nombre_setter", "")
        if nombre_actual.strip().lower() in ("desconocido", "", "none"):
            call_id = str(s.get("ID Llamada") or s.get("id_fathom") or "")
            nombre_correcto = mapa_nombres.get(call_id)
            if nombre_correcto and nombre_correcto.lower() != "desconocido":
                record_id = s.get("Id") or s.get("id")
                try:
                    actualizar_registro("calificaciones_setters", record_id, {"Setter": nombre_correcto})
                    print(f"  ✅ Setter ID {record_id}: 'Desconocido' → '{nombre_correcto}'")
                    setters_corregidos += 1
                except Exception as e:
                    print(f"  ⚠️  Error actualizando setter ID {record_id}: {e}")
            else:
                print(f"  ℹ️  Setter ID {s.get('Id')}: no se encontró nombre para call_id={call_id}")
    print(f"  → {setters_corregidos} setters corregidos.\n")

    print(f"=== COMPLETADO: {closers_corregidos + setters_corregidos} registros corregidos ===")

if __name__ == "__main__":
    corregir_desconocidos()
