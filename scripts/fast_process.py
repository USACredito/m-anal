import os
import sys
import time
from datetime import datetime
from pprint import pprint

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.nocodb_client import listar_registros
from scripts.transcripcion import descargar_audio, transcribir_con_deepgram, actualizar_registro
from scripts.calificaciones import calificar_ventas

def process_target_calls():
    print("Buscando llamadas del 2026-04-01 y 2026-04-07 para procesarlas rapido...")
    todas = listar_registros("llamadas_ventas")
    
    # Encontrar algunas de esas fechas que no estén analizadas
    objetivos = []
    
    for c in todas:
        f = c.get("Fecha")
        # Mirar 1-2 llamadas del 04-07 y del 04-01 que tengan URL de grabacion pero sin texto
        if f in ("2026-04-07", "2026-04-01"):
            t = c.get("Transcripción Texto")
            u = c.get("URL Grabación")
            estado = c.get("Estado")
            
            if u and not t and estado != 'error_transcripcion':
                objetivos.append(c)
                if len(objetivos) >= 5: # Procemos 5
                    break
                    
    print(f"Encontré {len(objetivos)} llamadas objetivo a procesar.")
    
    procesadas = []
    
    for r in objetivos:
        try:
            nocodb_id = r.get("Id")
            call_id   = r.get("ID Fathom") or str(nocodb_id)
            url_audio = r.get("URL Grabación", "")
            titulo    = r.get("Título", "")
            
            print(f"--- Procesando {call_id} del {r.get('Fecha')} ---")
            
            # Descargar
            ruta_local = descargar_audio(url_audio, call_id, titulo)
            if not ruta_local:
                print("No se pudo descargar audio.")
                continue

            # Transcribir
            texto = transcribir_con_deepgram(ruta_local, call_id)

            if texto:
                texto_final = texto[:30000]
                actualizar_registro("llamadas_ventas", nocodb_id, {
                    "Transcripción Texto": texto_final,
                    "Estado": "transcrito",
                    "Fecha Procesamiento": datetime.now().strftime("%Y-%m-%d")
                })
                print(f"[OK] [{call_id}] Transcrita.")
                
                # Actualizar el objeto memory cache para pasar a IA
                r["Transcripción Texto"] = texto_final
                r["Estado"] = "transcrito"
                procesadas.append(r)
            
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
                
        except Exception as e:
            print(f"Error con llamada {r.get('ID Fathom')}: {e}")
            
    print(f"Llamadas procesadas: {len(procesadas)}. Ejecutando análisis IA...")
    if procesadas:
        calificar_ventas(procesadas)
        for p in procesadas:
            actualizar_registro("llamadas_ventas", p.get("Id"), {"Estado": "analizado"})
    print("FINISHED")

if __name__ == "__main__":
    process_target_calls()

