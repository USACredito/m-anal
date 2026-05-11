"""
scripts/descargar_grabaciones_mayo.py
Descarga TODAS las grabaciones de mayo 2026 desde RingCentral y Aircall.

Diseño conservador para no saturar las APIs:
  - RC : ~2s entre requests al call-log y a recording/content (heavy API tier).
  - AC : ~1s entre requests (límite default 60/min).
  - Backoff exponencial en 429 / 5xx respetando Retry-After.
  - Idempotente: si el archivo ya existe, se salta (reanudable).
  - Paginación completa hasta que la fuente diga "no hay más".

Salida:
  grabaciones/mayo_2026/rc/<call_id>.mp3
  grabaciones/mayo_2026/aircall/<call_id>.mp3
  grabaciones/mayo_2026/index.csv     (id, fuente, fecha, duración, agente, ruta)

Uso:
  python scripts/descargar_grabaciones_mayo.py                # ambos proveedores
  python scripts/descargar_grabaciones_mayo.py --solo rc
  python scripts/descargar_grabaciones_mayo.py --solo aircall
  python scripts/descargar_grabaciones_mayo.py --inicio 2026-05-01 --fin 2026-05-31
"""

import argparse
import base64
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

RC_CLIENT_ID     = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_JWT           = os.getenv("RC_JWT")
RC_SERVER_URL    = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")

AIRCALL_ID    = os.getenv("AIRCALL_ID")
AIRCALL_TOKEN = os.getenv("AIRCALL_TOKEN")
AIRCALL_BASE  = "https://api.aircall.io/v1"

# Ritmos conservadores (segundos entre requests)
RC_DELAY      = 2.0   # heavy tier ≈ 10 req/min
RC_DL_DELAY   = 3.0   # descarga de audio, todavía más conservador
AC_DELAY      = 1.0   # default 60 req/min

MAX_REINTENTOS = 5
TIMEOUT_HTTP   = 60

OUT_DIR = Path(__file__).resolve().parents[1] / "grabaciones" / "mayo_2026"


# ─── UTILIDADES COMUNES ───────────────────────────────────────────────────────

def _esperar(s: float) -> None:
    if s > 0:
        time.sleep(s)


def _backoff(intento: int, retry_after: float | None = None) -> float:
    """Espera respetando Retry-After si viene, sino backoff exponencial."""
    if retry_after is not None:
        return max(1.0, retry_after)
    return min(60.0, 2 ** intento)


def _request_con_reintentos(metodo: str, url: str, *, headers=None, params=None,
                             data=None, auth=None, stream=False) -> requests.Response | None:
    """GET/POST con reintentos en 429/5xx. Devuelve la respuesta final o None."""
    for intento in range(MAX_REINTENTOS):
        try:
            resp = requests.request(
                metodo, url,
                headers=headers, params=params, data=data, auth=auth,
                stream=stream, timeout=TIMEOUT_HTTP,
            )
        except requests.RequestException as e:
            espera = _backoff(intento)
            print(f"    [RETRY] {e} — durmiendo {espera:.0f}s")
            _esperar(espera)
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            ra = resp.headers.get("Retry-After")
            espera = _backoff(intento, float(ra) if ra and ra.isdigit() else None)
            print(f"    [HTTP {resp.status_code}] esperando {espera:.0f}s (intento {intento+1}/{MAX_REINTENTOS})")
            _esperar(espera)
            continue

        return resp

    print(f"    [FAIL] Se agotaron reintentos en {url}")
    return None


def _escribir_indice(filas: list[dict]) -> None:
    if not filas:
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ruta = OUT_DIR / "index.csv"
    nuevo = not ruta.exists()
    with ruta.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fuente", "id", "fecha", "duracion_seg", "agente", "ruta"])
        if nuevo:
            w.writeheader()
        for fila in filas:
            w.writerow(fila)


# ─── RINGCENTRAL ──────────────────────────────────────────────────────────────

_RC_TOKEN_FILE = "/app/.tmp/rc_token.json"


def _rc_obtener_token() -> str | None:
    """Reutiliza el token en disco si está fresco (evita CMN-301)."""
    try:
        os.makedirs(os.path.dirname(_RC_TOKEN_FILE), exist_ok=True)
    except Exception:
        pass

    if os.path.exists(_RC_TOKEN_FILE):
        try:
            with open(_RC_TOKEN_FILE) as f:
                saved = json.load(f)
            if time.time() < saved.get("expires_at", 0):
                return saved["access_token"]
        except Exception:
            pass

    if not (RC_CLIENT_ID and RC_CLIENT_SECRET and RC_JWT):
        print("[RC] Faltan credenciales (RC_CLIENT_ID/SECRET/JWT).")
        return None

    auth_header = base64.b64encode(f"{RC_CLIENT_ID}:{RC_CLIENT_SECRET}".encode()).decode()
    resp = _request_con_reintentos(
        "POST",
        f"{RC_SERVER_URL}/restapi/oauth/token",
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": RC_JWT,
        },
    )
    if not resp or resp.status_code != 200:
        print(f"[RC] No se pudo obtener token: {resp.text if resp else 'sin respuesta'}")
        return None

    td = resp.json()
    try:
        with open(_RC_TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": td["access_token"],
                "expires_at": time.time() + td.get("expires_in", 3600) - 300,
            }, f)
    except Exception:
        pass
    return td["access_token"]


def descargar_rc(date_from: str, date_to: str) -> list[dict]:
    """Recorre call-log RC y descarga audio de cada llamada con grabación."""
    token = _rc_obtener_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    salida_dir = OUT_DIR / "rc"
    salida_dir.mkdir(parents=True, exist_ok=True)

    indice: list[dict] = []
    pagina = 1
    descargadas = 0
    saltadas = 0
    sin_grabacion = 0

    while True:
        params = {
            "dateFrom": f"{date_from}T00:00:00.000Z",
            "dateTo":   f"{date_to}T23:59:59.999Z",
            "withRecording": "true",
            "perPage": 250,
            "page": pagina,
        }
        print(f"\n[RC] Pidiendo call-log página {pagina} ({date_from} → {date_to})")
        resp = _request_con_reintentos(
            "GET",
            f"{RC_SERVER_URL}/restapi/v1.0/account/~/call-log",
            headers=headers, params=params,
        )
        _esperar(RC_DELAY)
        if not resp or resp.status_code != 200:
            print(f"[RC] Error al listar: {resp.text if resp else 'sin respuesta'}")
            break

        data = resp.json()
        registros = data.get("records", [])
        if not registros:
            print(f"[RC] Página {pagina}: 0 registros, fin.")
            break

        print(f"[RC] Página {pagina}: {len(registros)} llamadas.")

        for call in registros:
            call_id = str(call.get("id"))
            recording = call.get("recording") or {}
            rec_id = recording.get("id")
            if not rec_id:
                sin_grabacion += 1
                continue

            fecha = (call.get("startTime") or "")[:10]
            duracion = int(call.get("duration", 0))
            from_name = (call.get("from") or {}).get("name", "Desconocido")
            to_name   = (call.get("to")   or {}).get("name", "Desconocido")

            destino = salida_dir / f"{call_id}.mp3"
            if destino.exists() and destino.stat().st_size > 0:
                saltadas += 1
                indice.append({
                    "fuente": "rc", "id": call_id, "fecha": fecha,
                    "duracion_seg": duracion,
                    "agente": f"{from_name} -> {to_name}",
                    "ruta": str(destino.relative_to(OUT_DIR.parent)),
                })
                continue

            url_audio = f"{RC_SERVER_URL}/restapi/v1.0/account/~/recording/{rec_id}/content"
            print(f"  [RC] Descargando {call_id} ({duracion}s)…")
            r = _request_con_reintentos("GET", url_audio, headers=headers, stream=True)
            _esperar(RC_DL_DELAY)
            if not r or r.status_code != 200:
                print(f"    [WARN] No se pudo descargar {call_id}: {r.status_code if r else '-'}")
                continue

            tmp = destino.with_suffix(".mp3.part")
            try:
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            f.write(chunk)
                tmp.replace(destino)
                descargadas += 1
                indice.append({
                    "fuente": "rc", "id": call_id, "fecha": fecha,
                    "duracion_seg": duracion,
                    "agente": f"{from_name} -> {to_name}",
                    "ruta": str(destino.relative_to(OUT_DIR.parent)),
                })
            except Exception as e:
                print(f"    [ERROR] escribiendo {destino}: {e}")
                if tmp.exists():
                    tmp.unlink(missing_ok=True)

        navigation = (data.get("navigation") or {})
        if not navigation.get("nextPage"):
            break
        pagina += 1

    print(f"\n[RC] Resumen — descargadas: {descargadas} | ya existían: {saltadas} | sin grabación: {sin_grabacion}")
    return indice


# ─── AIRCALL ──────────────────────────────────────────────────────────────────

def descargar_aircall(date_from: str, date_to: str) -> list[dict]:
    if not (AIRCALL_ID and AIRCALL_TOKEN):
        print("[Aircall] Faltan credenciales (AIRCALL_ID/AIRCALL_TOKEN).")
        return []

    auth = (AIRCALL_ID, AIRCALL_TOKEN)
    salida_dir = OUT_DIR / "aircall"
    salida_dir.mkdir(parents=True, exist_ok=True)

    ts_from = int(datetime.strptime(date_from, "%Y-%m-%d").timestamp())
    ts_to   = int((datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)).timestamp()) - 1

    indice: list[dict] = []
    page = 1
    descargadas = 0
    saltadas = 0
    sin_grabacion = 0

    while True:
        params = {
            "from": ts_from,
            "to": ts_to,
            "per_page": 50,
            "page": page,
            "order": "asc",
        }
        print(f"\n[Aircall] Página {page} ({date_from} → {date_to})")
        resp = _request_con_reintentos("GET", f"{AIRCALL_BASE}/calls", auth=auth, params=params)
        _esperar(AC_DELAY)
        if not resp or resp.status_code != 200:
            print(f"[Aircall] Error al listar: {resp.text if resp else 'sin respuesta'}")
            break

        data = resp.json()
        calls = data.get("calls", [])
        if not calls:
            print(f"[Aircall] Página {page}: 0 llamadas, fin.")
            break

        print(f"[Aircall] Página {page}: {len(calls)} llamadas.")

        for call in calls:
            call_id = str(call.get("id"))
            url_audio = call.get("recording")
            if not url_audio:
                sin_grabacion += 1
                continue

            fecha = datetime.fromtimestamp(call.get("started_at", 0)).strftime("%Y-%m-%d")
            duracion = int(call.get("duration", 0))
            user_name      = (call.get("user") or {}).get("name", "Desconocido")
            contact_number = call.get("raw_digits", "Privado")

            destino = salida_dir / f"{call_id}.mp3"
            if destino.exists() and destino.stat().st_size > 0:
                saltadas += 1
                indice.append({
                    "fuente": "aircall", "id": call_id, "fecha": fecha,
                    "duracion_seg": duracion,
                    "agente": f"{user_name} -> {contact_number}",
                    "ruta": str(destino.relative_to(OUT_DIR.parent)),
                })
                continue

            print(f"  [AC] Descargando {call_id} ({duracion}s)…")
            r = _request_con_reintentos("GET", url_audio, stream=True)
            _esperar(AC_DELAY)
            if not r or r.status_code != 200:
                print(f"    [WARN] No se pudo descargar {call_id}: {r.status_code if r else '-'}")
                continue

            tmp = destino.with_suffix(".mp3.part")
            try:
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            f.write(chunk)
                tmp.replace(destino)
                descargadas += 1
                indice.append({
                    "fuente": "aircall", "id": call_id, "fecha": fecha,
                    "duracion_seg": duracion,
                    "agente": f"{user_name} -> {contact_number}",
                    "ruta": str(destino.relative_to(OUT_DIR.parent)),
                })
            except Exception as e:
                print(f"    [ERROR] escribiendo {destino}: {e}")
                if tmp.exists():
                    tmp.unlink(missing_ok=True)

        meta = data.get("meta") or {}
        if not meta.get("next_page_link"):
            break
        page += 1

    print(f"\n[Aircall] Resumen — descargadas: {descargadas} | ya existían: {saltadas} | sin grabación: {sin_grabacion}")
    return indice


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Descarga grabaciones de mayo 2026 (RC + Aircall).")
    parser.add_argument("--inicio", default="2026-05-01", help="Fecha inicio YYYY-MM-DD (default 2026-05-01)")
    parser.add_argument("--fin",    default="2026-05-31", help="Fecha fin YYYY-MM-DD (default 2026-05-31)")
    parser.add_argument("--solo", choices=["rc", "aircall"], help="Procesar un solo proveedor")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"""
==============================================================
  DESCARGA DE GRABACIONES — {args.inicio} → {args.fin}
  Carpeta destino: {OUT_DIR}
  Ritmo RC:      {RC_DELAY}s listar / {RC_DL_DELAY}s descarga
  Ritmo Aircall: {AC_DELAY}s
==============================================================
""")

    indice_total: list[dict] = []
    if args.solo in (None, "rc"):
        indice_total += descargar_rc(args.inicio, args.fin)
    if args.solo in (None, "aircall"):
        indice_total += descargar_aircall(args.inicio, args.fin)

    _escribir_indice(indice_total)
    print(f"\n[OK] Índice escrito en {OUT_DIR / 'index.csv'} ({len(indice_total)} filas).")


if __name__ == "__main__":
    main()
