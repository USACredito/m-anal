import sys
sys.path.append(".")
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from scripts.nocodb_client import crear_registro, listar_registros

load_dotenv()

# Nombres extraídos de capturas / logs recientes
nombres_closers = [
    "Nora castillo",
    "Carlos Perez",
    "Gianella Romero",
    "Nordelys Rodriguez",
    "Carlen Gonzalez",
    "Edduar Peña",
    "DELGADO LUISA",
    "CIVIL SERGE", 
    "Yelitza castillo",
    "Roque Vargas",
    "VASQUEZ LABARCA",
    "Victor Cuauro",
    "Francelis Sanchez",
    "Agente Setter",          # Fue visto en un log de Aircall
    "Customer Experience",    # Visto en llamadas Aircall/RC
    "WIRELESS CALLER"         # Podría ser externo pero lo agregamos por si era extensión
]

def format_email(nombre):
    limpio = nombre.lower().replace(" ", ".").replace("ñ", "n").replace("peña", "pena")
    return f"{limpio}@usacredito.com"

print("Comprobando existentes...")
try:
    existentes = [d.get("Nombre") for d in listar_registros("agentes")]
    
    agregados = 0
    for nombre in nombres_closers:
        if nombre not in existentes:
            # Crear
            data = {
                "Nombre": nombre,
                "Tipo": "Ventas",   # Identificado como Sales/Closer en el prompt (la variable en el viejo era 'closer' o 'Ventas' en sync)
                # OJO: La tabla actual devolvió "Tipo: 'closer'", usaré "closer" para ser consistente
                "Activo": True,
                "Email Fathom": format_email(nombre),
                "Fecha Registro": datetime.now().strftime("%Y-%m-%d")
            }
            # Reasignamos a 'closer' porque en la tabla vimos que los actuales tienen 'closer'
            data["Tipo"] = "closer"
            
            crear_registro("agentes", data)
            print(f"✅ Agente registrado: {nombre}")
            agregados += 1
        else:
            print(f"Ya existe: {nombre}")
            
    print(f"\nFinalizado. {agregados} agentes nuevos agregados.")
except Exception as e:
    import traceback
    traceback.print_exc()
