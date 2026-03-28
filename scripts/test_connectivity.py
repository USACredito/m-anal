"""
scripts/test_connectivity.py
Prueba de conexión para ClickUp, RingCentral (JWT) y Aircall.
"""

import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def test_clickup():
    print("--- [CLICKUP] Probando Conexión ---")
    token = os.getenv("CLICKUP_API_TOKEN")
    if not token:
        print("ERROR: CLICKUP_API_TOKEN no encontrado en .env")
        return False
    
    url = "https://api.clickup.com/api/v2/user"
    headers = {"Authorization": token}
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            user_data = resp.json()
            print(f"ÉXITO: Conectado a ClickUp como {user_data.get('user', {}).get('username')} ({user_data.get('user', {}).get('email')})")
            return True
        else:
            print(f"FALLO: Error {resp.status_code} al conectar a ClickUp.")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def test_ringcentral():
    print("\n--- [RINGCENTRAL] Probando Conexión (JWT Flow) ---")
    client_id = os.getenv("RC_CLIENT_ID")
    client_secret = os.getenv("RC_CLIENT_SECRET")
    jwt_token = os.getenv("RC_JWT")
    server_url = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")
    
    if not client_id or not client_secret or not jwt_token:
        print("ERROR: Faltan credenciales de RingCentral (ClientID, Secret o JWT) en .env")
        return False
    
    # Endpoint de obtención de token
    url = f"{server_url}/restapi/oauth/token"
    
    # Auth header básico (ID:Secret)
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Data para el grant type JWT
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token
    }
    
    try:
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code == 200:
            print("ÉXITO: Conectado a RingCentral (Access Token obtenido correctamente)")
            
            # Prueba adicional: Obtener información del usuario dueño del token
            access_token = resp.json().get("access_token")
            me_url = f"{server_url}/restapi/v1.0/account/~/extension/~"
            me_resp = requests.get(me_url, headers={"Authorization": f"Bearer {access_token}"})
            
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                nombre = me_data.get("contact", {}).get("firstName", "") + " " + me_data.get("contact", {}).get("lastName", "")
                print(f"Info: Identificado como {nombre.strip()} ({me_data.get('contact', {}).get('email', 'N/A')})")
            
            return True
        else:
            print(f"FALLO: Error {resp.status_code} al conectar a RingCentral.")
            print(f"Respuesta: {resp.text}")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def test_aircall():
    print("\n--- [AIRCALL] Probando Conexión ---")
    aircall_id = os.getenv("AIRCALL_ID")
    aircall_token = os.getenv("AIRCALL_TOKEN")
    
    if not aircall_id or not aircall_token:
        print("ERROR: Credenciales de Aircall no encontradas en .env")
        return False
    
    url = "https://api.aircall.io/v1/users"
    
    try:
        resp = requests.get(url, auth=(aircall_id, aircall_token))
        if resp.status_code == 200:
            print("ÉXITO: Conectado a Aircall correctamente.")
            return True
        else:
            print(f"FALLO: Error {resp.status_code} al conectar a Aircall.")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    c_res = test_clickup()
    r_res = test_ringcentral()
    a_res = test_aircall()
    
    if c_res and r_res and a_res:
        print("\n✅ Todas las conexiones verificadas con éxito.")
    else:
        print("\n❌ Algunas conexiones fallaron.")
