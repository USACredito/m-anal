"""
main.py — ORQUESTADOR PRINCIPAL
Ejecuta el pipeline completo de análisis de llamadas:
  1. Sincronización de llamadas (RingCentral y Aircall)
  2. Transcripción de llamadas pendientes (Gemini)
  3. Análisis de texto con Gemini
  4. Calificaciones de calidad en NocoDB

Nota: ClickUp deshabilitado. Los datos van solo a NocoDB y al Dashboard.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta

def correr_script(nombre: str, args_extra: list) -> bool:
    """Ejecuta un script de la carpeta scripts/ con los argumentos dados."""
    script_path = os.path.join(os.path.dirname(__file__), "scripts", nombre)
    if not os.path.exists(script_path):
        print(f"[ERROR] No se encuentra el script: {script_path}")
        return False
        
    cmd = [sys.executable, script_path] + args_extra
    print(f"\n{'='*60}")
    print(f"▶ Ejecutando: {nombre}")
    print(f"{'='*60}")
    
    # Heredar el entorno para asegurar que las variables de .env se lean correctamente si es necesario
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"[ERROR] {nombre} terminó con código {result.returncode}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Análisis de Llamadas — Pipeline completo"
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--inicio", help="Fecha inicio (YYYY-MM-DD)")
    grupo.add_argument("--hoy", action="store_true", help="Analizar solo el día de hoy")
    grupo.add_argument("--semana", action="store_true", help="Analizar los últimos 7 días")

    parser.add_argument("--fin", help="Fecha fin (YYYY-MM-DD), requerido si se usa --inicio")
    parser.add_argument("--solo", choices=["sync", "transcripcion", "gemini", "reportes", "emails", "calificaciones"],
                        help="Ejecutar solo una etapa del pipeline")

    args = parser.parse_args()

    # Calcular rango de fechas
    hoy = datetime.now().strftime("%Y-%m-%d")

    if args.hoy:
        fecha_inicio = hoy
        fecha_fin = hoy
    elif args.semana:
        # Lunes de esta semana (no 7 días atrás)
        hoy_dt = datetime.now()
        lunes = hoy_dt - timedelta(days=hoy_dt.weekday())
        fecha_inicio = lunes.strftime("%Y-%m-%d")
        fecha_fin = hoy
    else:
        if not args.fin:
            print("[ERROR] Debes especificar --fin cuando usas --inicio")
            sys.exit(1)
        fecha_inicio = args.inicio
        fecha_fin = args.fin

    fecha_args = ["--inicio", fecha_inicio, "--fin", fecha_fin]

    print(f"""
╔══════════════════════════════════════════════════════════╗
║     SISTEMA DE ANÁLISIS DE LLAMADAS — ANTIGRAVITY        ║
╠══════════════════════════════════════════════════════════╣
║  Período: {fecha_inicio} → {fecha_fin}
║  Inicio:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╚══════════════════════════════════════════════════════════╝
""")

    # Definir etapas del pipeline
    # sync_ringcentral y sync_aircall se ejecutan en la etapa 'sync'
    pipeline = []
    
    if args.solo == "sync" or not args.solo:
        pipeline.append(("sync-rc", "sync_ringcentral.py"))
        pipeline.append(("sync-ac", "sync_aircall.py"))
    
    pipeline.extend([
        ("transcripcion", "transcripcion.py"),
        ("gemini", "analisis_gemini.py"),
        ("calificaciones", "calificaciones.py"),
        # ClickUp eliminado — datos van solo a NocoDB y Dashboard
    ])

    if args.solo and args.solo != "sync":
        pipeline = [(k, v) for k, v in pipeline if k == args.solo]

    errores = []
    for etapa, script in pipeline:
        # Los scripts de sincronización no usan fecha_args por ahora (traen lo último)
        # pero los demás sí los necesitan.
        current_args = fecha_args if "sync" not in etapa else []
        exito = correr_script(script, current_args)
        if not exito:
            errores.append(etapa)

    # Resumen final
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    RESUMEN FINAL                         ║
╠══════════════════════════════════════════════════════════╣
║  Período:   {fecha_inicio} → {fecha_fin}
║  Etapas OK: {len(pipeline) - len(errores)}/{len(pipeline)}
║  Errores:   {', '.join(errores) if errores else 'Ninguno'}
║  Fin:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╚══════════════════════════════════════════════════════════╝
""")

    if errores:
        sys.exit(1)

if __name__ == "__main__":
    main()
