"""
scripts/agentes_config.py
Lista definitiva de setters y closers del equipo.
Este módulo es la fuente de verdad para clasificar llamadas.
"""

# Nombres normalizados (en minúsculas para comparación).
# Se acepta coincidencia parcial: si cualquier token de la lista
# aparece en el nombre del participante, se clasifica.

SETTERS = [
    "ridchell ladera",
    "gianella romero",
    "yanela romero",       # variante común de gianella
    "edduar pena",
    "edduar peña",
    "nora castillo",
    "norddelys rodriguez",
    "norddelys rodríguez",
    "roque vargas",
    "marianny cuauro",
    "victor cuauro",
    "víctor cuauro",
]

CLOSERS = [
    "carolina santana",
    "carlen gonzalez",
    "carlen gonzález",
    "francelis sanchez",
    "francelís sanchez",
    "francelis sánchez",
    "juan martinez",
    "juan martínez",
    "jesus medina",
    "jesús medina",
    "anakarina kristen",
    "yelitza castillo",
    "grey hernandez",
    "grey hernández",
    "leopoldo aponte",
    "leopoldo",            # aparece solo en algunas llamadas
    "patricia medina",
]


def clasificar_participante(nombre: str) -> str:
    """
    Dado el nombre de un participante, retorna 'setter', 'closer' o 'desconocido'.
    Compara en minúsculas y acepta coincidencia parcial por token.
    """
    nombre_lower = nombre.lower().strip()

    for s in SETTERS:
        # Coincidencia exacta o substring
        if s in nombre_lower or nombre_lower in s:
            return "setter"
        # Coincidencia por primer apellido (ej: "roque vargas escalona" → "roque vargas")
        tokens_config = s.split()
        if all(t in nombre_lower for t in tokens_config):
            return "setter"

    for c in CLOSERS:
        if c in nombre_lower or nombre_lower in c:
            return "closer"
        tokens_config = c.split()
        if all(t in nombre_lower for t in tokens_config):
            return "closer"

    return "desconocido"


def clasificar_llamada(from_name: str, to_name: str) -> str:
    """
    Clasifica una llamada revisando ambos participantes.
    Retorna 'setter', 'closer' o 'ventas' (fallback).
    """
    for nombre in [from_name, to_name]:
        tipo = clasificar_participante(nombre)
        if tipo != "desconocido":
            return tipo
    return "ventas"
