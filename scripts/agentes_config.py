"""
scripts/agentes_config.py
Lista definitiva de setters y closers del equipo.
Este módulo es la fuente de verdad para clasificar llamadas.
"""

import unicodedata

def _norm(s: str) -> str:
    """Minúsculas + elimina tildes para comparación robusta."""
    return unicodedata.normalize("NFD", s.lower().strip()).encode("ascii", "ignore").decode()

SETTERS = [
    "ridchell ladera",
    "gianella romero",
    "yanela romero",
    "edduar pena",
    "nora castillo",
    "norddelys rodriguez",
    "roque vargas",
    "marianny cuauro",
    "victor cuauro",
]

CLOSERS = [
    "carolina santana",
    "carlen gonzalez",
    "francelis sanchez",
    "juan martinez",
    "jesus medina",
    "anakarina kristen",
    "yelitza castillo",
    "grey hernandez",
    "leopoldo aponte",
    "leopoldo",
    "patricia medina",
]


def clasificar_participante(nombre: str) -> str:
    """
    Dado el nombre de un participante, retorna 'setter', 'closer' o 'desconocido'.
    Compara sin tildes y acepta coincidencia por todos los tokens del nombre config.
    """
    nombre_norm = _norm(nombre)

    for s in SETTERS:
        tokens = _norm(s).split()
        if all(t in nombre_norm for t in tokens):
            return "setter"

    for c in CLOSERS:
        tokens = _norm(c).split()
        if all(t in nombre_norm for t in tokens):
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
