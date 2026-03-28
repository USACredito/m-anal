import os
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# Configuración desde .env
FULL_URL = os.getenv("NOCODB_URL", "")
API_TOKEN = os.getenv("NOCODB_API_TOKEN", "")

# Extraer Project ID
PROJECT_ID = "p9sqt7wk1bkr0lq"
if "/nc/" in FULL_URL:
    PROJECT_ID = FULL_URL.split("/nc/")[-1].split("/")[0]

BASE_API_URL = FULL_URL.split("/dashboard")[0] + "/api/v1"

HEADERS = {
    "xc-token": API_TOKEN,
    "Content-Type": "application/json"
}

def insertar_agente(nombre, tipo, email):
    # Usando el ID de tabla en lugar de nombre para asegurar compatibilidad
    TABLE_ID_AGENTES = "mabd7x8ql6q6rxj"
    url = f"{BASE_API_URL}/db/data/noco/{PROJECT_ID}/{TABLE_ID_AGENTES}"
    payload = {
        "nombre": nombre,
        "tipo": tipo,
        "email_fathom": email,
        "activo": True,
        "fecha_registro": date.today().isoformat()
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        print(f"  [OK] Agente {nombre} insertado.")
    else:
        print(f"  [ERROR] No se pudo insertar a {nombre}: {resp.text}")

def main():
    print("--- INSERTANDO DATOS DE PRUEBA ---")
    
    agentes = [
        ("Carlos Méndez", "closer", "carlos@empresa.com"),
        ("Laura Gómez", "closer", "laura@empresa.com"),
        ("Miguel Torres", "soporte", "miguel@empresa.com"),
        ("Pedro Salinas", "onboarding", "pedro@empresa.com"),
    ]
    
    for n, t, e in agentes:
        insertar_agente(n, t, e)
    
    print("\n--- DATOS LISTOS ---")

if __name__ == "__main__":
    main()
