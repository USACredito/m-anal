"""
scripts/agentes_config.py
Fuente de verdad para clasificar llamadas como setter/closer.
Usa IDs exactos de RingCentral y Aircall — sin fuzzy matching.
"""

# ── RingCentral extension IDs ────────────────────────────────────────────────
RC_SETTER_IDS = {
    1029170035,   # Ridchell Ladera
    1206617035,   # Gianella Romero
    1122516035,   # Edduar Peña
    1029162035,   # Nora Castillo
    1029160035,   # Nordelys Rodriguez
    1206615035,   # Roque Vargas Escalona
    1209636035,   # Marianny Cuauro
    474394034,    # Victor Cuauro
}

RC_CLOSER_IDS = {
    1029153035,   # Carolina Santana
    740322035,    # Carlen Gonzalez
    1029175035,   # Francelis Sanchez
    1029177035,   # Juan Raúl Martínez
    439646034,    # Jesus Medina
    413051034,    # Ana Karina Kristen
    1029168035,   # Yelitza Castillo
    804130035,    # Leopoldo Aponte
    1029172035,   # Patricia Medina
}

# ── Aircall user IDs ─────────────────────────────────────────────────────────
AC_SETTER_IDS = {
    1707057,      # Agente Setter (cuenta genérica)
    1905359,      # Gianella Romero
    1786710,      # Norddelys Rodriguez
    1905361,      # Roque Vargas
    1867867,      # Victor Cuauro
}

AC_CLOSER_IDS = {
    1789232,      # Francelis Sanchez
    1789233,      # Yelitza Castillo
}


def clasificar_por_rc_id(ext_id) -> str:
    """Clasifica un agente RC por su extensionId. Retorna 'setter', 'closer' o 'desconocido'."""
    if ext_id is None:
        return "desconocido"
    try:
        eid = int(ext_id)
    except (ValueError, TypeError):
        return "desconocido"
    if eid in RC_SETTER_IDS:
        return "setter"
    if eid in RC_CLOSER_IDS:
        return "closer"
    return "desconocido"


def clasificar_por_aircall_id(user_id) -> str:
    """Clasifica un agente Aircall por su user ID. Retorna 'setter', 'closer' o 'desconocido'."""
    if user_id is None:
        return "desconocido"
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return "desconocido"
    if uid in AC_SETTER_IDS:
        return "setter"
    if uid in AC_CLOSER_IDS:
        return "closer"
    return "desconocido"


def clasificar_llamada_rc(from_ext_id, to_ext_id) -> str:
    """
    Clasifica una llamada RC revisando from y to por extensionId.
    Retorna 'setter', 'closer' o 'ventas'.
    """
    for eid in [from_ext_id, to_ext_id]:
        tipo = clasificar_por_rc_id(eid)
        if tipo != "desconocido":
            return tipo
    return "ventas"


def clasificar_llamada_aircall(user_id) -> str:
    """
    Clasifica una llamada Aircall por el user_id del agente.
    Retorna 'setter', 'closer' o 'ventas'.
    """
    tipo = clasificar_por_aircall_id(user_id)
    return tipo if tipo != "desconocido" else "ventas"


# ── Compatibilidad con fix_tipo_llamadas.py (basado en nombres) ──────────────
import unicodedata

def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s.lower().strip()).encode("ascii", "ignore").decode()

_RC_SETTER_NAMES = [_norm(n) for n in [
    "ridchell ladera", "gianella romero", "yanela romero", "edduar pena",
    "nora castillo", "norddelys rodriguez", "roque vargas", "marianny cuauro", "victor cuauro",
]]
_RC_CLOSER_NAMES = [_norm(n) for n in [
    "carolina santana", "carlen gonzalez", "francelis sanchez", "juan martinez",
    "jesus medina", "anakarina kristen", "ana karina kristen", "yelitza castillo",
    "leopoldo aponte", "leopoldo", "patricia medina",
]]

def clasificar_llamada(from_name: str, to_name: str) -> str:
    """Fallback por nombre para fix_tipo_llamadas.py sobre registros históricos."""
    for nombre in [from_name, to_name]:
        n = _norm(nombre)
        for s in _RC_SETTER_NAMES:
            if all(t in n for t in s.split()):
                return "setter"
        for c in _RC_CLOSER_NAMES:
            if all(t in n for t in c.split()):
                return "closer"
    return "ventas"
