"""
scripts/listar_agentes_ids.py
Lista todos los agentes/extensiones de RC y Aircall con sus IDs exactos.
Ejecutar una vez para obtener los IDs que se configuran en agentes_config.py.
"""

import os, sys, requests, base64
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def listar_rc():
    RC_CLIENT_ID     = os.getenv("RC_CLIENT_ID")
    RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
    RC_JWT           = os.getenv("RC_JWT")
    RC_SERVER_URL    = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")

    if not RC_CLIENT_ID:
        print("[RC] Credenciales no encontradas, saltando.")
        return

    auth_header = base64.b64encode(f"{RC_CLIENT_ID}:{RC_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        f"{RC_SERVER_URL}/restapi/oauth/token",
        headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": RC_JWT}
    )
    if resp.status_code != 200:
        print(f"[RC] Error obteniendo token: {resp.text}")
        return

    token = resp.json()["access_token"]
    resp2 = requests.get(
        f"{RC_SERVER_URL}/restapi/v1.0/account/~/extension",
        headers={"Authorization": f"Bearer {token}"},
        params={"perPage": 250, "type": "User", "status": "Enabled"}
    )
    if resp2.status_code != 200:
        print(f"[RC] Error listando extensiones: {resp2.text}")
        return

    exts = resp2.json().get("records", [])
    print(f"\n{'='*55}")
    print(f"  RINGCENTRAL — {len(exts)} extensiones activas")
    print(f"{'='*55}")
    print(f"  {'ID':<12} {'Extensión':<8} {'Nombre'}")
    print(f"  {'-'*50}")
    for e in sorted(exts, key=lambda x: x.get("name","").lower()):
        print(f"  {e.get('id',''):<12} {e.get('extensionNumber',''):<8} {e.get('name','')}")


def listar_aircall():
    AIRCALL_ID    = os.getenv("AIRCALL_ID")
    AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")

    if not AIRCALL_ID:
        print("[Aircall] Credenciales no encontradas, saltando.")
        return

    resp = requests.get(
        "https://api.aircall.io/v1/users",
        auth=(AIRCALL_ID, AIRCALL_TOKEN),
        params={"per_page": 100}
    )
    if resp.status_code != 200:
        print(f"[Aircall] Error: {resp.text}")
        return

    users = resp.json().get("users", [])
    print(f"\n{'='*55}")
    print(f"  AIRCALL — {len(users)} usuarios")
    print(f"{'='*55}")
    print(f"  {'ID':<12} {'Nombre':<25} {'Email'}")
    print(f"  {'-'*50}")
    for u in sorted(users, key=lambda x: x.get("name","").lower()):
        print(f"  {u.get('id',''):<12} {u.get('name',''):<25} {u.get('email','')}")


if __name__ == "__main__":
    listar_rc()
    listar_aircall()
    print(f"\n{'='*55}")
    print("  Copia los IDs de setters y closers en agentes_config.py")
    print(f"{'='*55}\n")
