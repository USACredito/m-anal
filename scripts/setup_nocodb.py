import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Configuración desde .env
# Extraer la base URL y el Project ID de la URL completa
FULL_URL = os.getenv("NOCODB_URL", "")
API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")

# Intentar parsear el Project ID de la URL (p9sqt7wk1bkr0lq)
PROJECT_ID = "p9sqt7wk1bkr0lq" 
if "/nc/" in FULL_URL:
    PROJECT_ID = FULL_URL.split("/nc/")[-1].split("/")[0]

# La URL de la API suele ser el dominio + /api
BASE_API_URL = FULL_URL.split("/dashboard")[0] + "/api/v1"

HEADERS = {
    "xc-token": API_TOKEN,
    "Content-Type": "application/json"
}

def create_table(name, title, columns):
    """Crea una tabla en NocoDB con sus columnas principales."""
    url = f"{BASE_API_URL}/db/meta/projects/{PROJECT_ID}/tables"
    
    # NocoDB v1 espera columns como lista de objetos con pv (primary key)
    # El campo 'Id' suele crearse automáticamente como PK autonumérico.
    
    payload = {
        "table_name": name,
        "title": title,
        "columns": columns
    }
    
    print(f"[*] Creando tabla: {title} ({name})...")
    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        print(f"  [OK] Tabla {name} creada.")
        return resp.json()
    else:
        print(f"  [ERROR] No se pudo crear {name}: {resp.text}")
        return None

def main():
    print(f"--- INICIALIZANDO NOCODB (Proyecto: {PROJECT_ID}) ---")
    
    # 1. Definición de Tablas y Columnas
    
    # TABLAS DE LLAMADAS (Estructura idéntica)
    col_llamadas = [
        {"column_name": "id_fathom", "title": "ID Fathom", "uidt": "SingleLineText"},
        {"column_name": "titulo", "title": "Título", "uidt": "SingleLineText"},
        {"column_name": "fecha", "title": "Fecha", "uidt": "Date"},
        {"column_name": "hora", "title": "Hora", "uidt": "SingleLineText"}, # Usamos text para HH:MM simple
        {"column_name": "duracion_minutos", "title": "Duración (min)", "uidt": "Number"},
        {"column_name": "participantes", "title": "Participantes", "uidt": "LongText"},
        {"column_name": "url_grabacion", "title": "URL Grabación", "uidt": "SingleLineText"},
        {"column_name": "url_transcripcion_fathom", "title": "URL Transcripción Fathom", "uidt": "SingleLineText"},
        {"column_name": "tipo", "title": "Tipo", "uidt": "SingleLineText"},
        {"column_name": "estado_procesamiento", "title": "Estado", "uidt": "SingleLineText"},
        {"column_name": "transcripcion_texto", "title": "Transcripción Texto", "uidt": "LongText"},
        {"column_name": "fecha_procesamiento", "title": "Fecha Procesamiento", "uidt": "Date"}
    ]
    
    tablas_llamadas = ["llamadas_ventas", "llamadas_soporte", "llamadas_onboarding"]
    for t in tablas_llamadas:
        create_table(t, t.replace("_", " ").title(), col_llamadas)

    # TABLA AGENTES
    col_agentes = [
        {"column_name": "nombre", "title": "Nombre", "uidt": "SingleLineText"},
        {"column_name": "tipo", "title": "Tipo", "uidt": "SingleLineText"},
        {"column_name": "email_fathom", "title": "Email Fathom", "uidt": "SingleLineText"},
        {"column_name": "activo", "title": "Activo", "uidt": "Checkbox", "default_value": "true"},
        {"column_name": "fecha_registro", "title": "Fecha Registro", "uidt": "Date"}
    ]
    create_table("agentes", "Agentes", col_agentes)

    # TABLAS DE CALIFICACIONES
    col_calif_leads = [
        {"column_name": "id_llamada_fathom", "title": "ID Llamada", "uidt": "SingleLineText"},
        {"column_name": "fecha_llamada", "title": "Fecha Llamada", "uidt": "Date"},
        {"column_name": "calificacion", "title": "Calificación", "uidt": "Number"},
        {"column_name": "nivel", "title": "Nivel", "uidt": "SingleLineText"},
        {"column_name": "justificacion", "title": "Justificación", "uidt": "LongText"},
        {"column_name": "factores_positivos", "title": "Positivos", "uidt": "LongText"},
        {"column_name": "factores_negativos", "title": "Negativos", "uidt": "LongText"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ]
    create_table("calificaciones_leads", "Calificaciones Leads", col_calif_leads)

    col_calif_closers = [
        {"column_name": "nombre_closer", "title": "Closer", "uidt": "SingleLineText"},
        {"column_name": "calificacion_total", "title": "Nota Total", "uidt": "Number"},
        {"column_name": "calificacion_rapport", "title": "Rapport", "uidt": "Number"},
        {"column_name": "calificacion_descubrimiento", "title": "Descubrimiento", "uidt": "Number"},
        {"column_name": "calificacion_presentacion", "title": "Presentación", "uidt": "Number"},
        {"column_name": "calificacion_objeciones", "title": "Objeciones", "uidt": "Number"},
        {"column_name": "calificacion_cierre", "title": "Cierre", "uidt": "Number"},
        {"column_name": "resultado", "title": "Resultado", "uidt": "SingleLineText"},
        {"column_name": "fecha_llamada", "title": "Fecha Llamada", "uidt": "Date"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ]
    create_table("calificaciones_closers", "Calificaciones Closers", col_calif_closers)

    col_calif_onb = [
        {"column_name": "nombre_coach", "title": "Coach", "uidt": "SingleLineText"},
        {"column_name": "calificacion_total", "title": "Nota Total", "uidt": "Number"},
        {"column_name": "calificacion_claridad", "title": "Claridad", "uidt": "Number"},
        {"column_name": "calificacion_adaptacion", "title": "Adaptación", "uidt": "Number"},
        {"column_name": "calificacion_completitud", "title": "Completitud", "uidt": "Number"},
        {"column_name": "calificacion_tiempo", "title": "Tiempo", "uidt": "Number"},
        {"column_name": "calificacion_satisfaccion", "title": "Satisfacción", "uidt": "Number"},
        {"column_name": "cliente_listo", "title": "Listo?", "uidt": "SingleLineText"},
        {"column_name": "fecha_llamada", "title": "Fecha Llamada", "uidt": "Date"},
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"}
    ]
    create_table("calificaciones_onboarding", "Calificaciones Onboarding", col_calif_onb)

    # TABLAS DE SOPORTE E HISTÓRICO
    create_table("lista_emails", "Lista Emails", [
        {"column_name": "nombre", "title": "Nombre", "uidt": "SingleLineText"},
        {"column_name": "email", "title": "Email", "uidt": "SingleLineText"},
        {"column_name": "recibe_ventas", "title": "Ventas", "uidt": "Checkbox"},
        {"column_name": "recibe_soporte", "title": "Soporte", "uidt": "Checkbox"},
        {"column_name": "recibe_onboarding", "title": "Onboarding", "uidt": "Checkbox"}
    ])

    create_table("resumen_mensual_calidad", "Resumen Mensual", [
        {"column_name": "mes_año", "title": "Mes-Año", "uidt": "SingleLineText"},
        {"column_name": "promedio_calidad_leads", "title": "Promedio Leads", "uidt": "Number"},
        {"column_name": "promedio_calidad_closers", "title": "Promedio Closers", "uidt": "Number"},
        {"column_name": "promedio_calidad_onboarding", "title": "Promedio Onboarding", "uidt": "Number"},
        {"column_name": "total_llamadas_ventas", "title": "Total Ventas", "uidt": "Number"},
        {"column_name": "total_llamadas_soporte", "title": "Total Soporte", "uidt": "Number"},
        {"column_name": "total_llamadas_onboarding", "title": "Total Onboarding", "uidt": "Number"}
    ])

    print("\n--- PROCESO FINALIZADO ---")
    print("Para verificar, abre el Dashboard: python dashboard/app.py")

if __name__ == "__main__":
    main()
