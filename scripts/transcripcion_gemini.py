"""
scripts/transcripcion_gemini.py
Usa Google Gemini 1.5 Flash para transcribir archivos de audio.
"""

import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configuración de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def transcribir_audio(ruta_audio):
    """
    Sube un archivo de audio a Gemini y solicita su transcripción.
    """
    if not os.path.exists(ruta_audio):
        print(f"ERROR: No se encuentra el archivo {ruta_audio}")
        return None

    print(f"--- [GEMINI] Subiendo archivo: {os.path.basename(ruta_audio)} ---")
    
    # 1. Subir el archivo a Google AI File API
    audio_file = genai.upload_file(path=ruta_audio)
    print(f"Archivo subido. ID: {audio_file.name}")

    # 2. Esperar a que el archivo sea procesado
    while audio_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        print("\nERROR: Falló el procesamiento del audio en Google Cloud.")
        return None

    print("\nProcesamiento completado. Generando transcripción...")

    # 3. Invocar al modelo (Gemini 1.5 Flash es ideal para esto)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    
    prompt = (
        "Eres un transcriptor experto. Escucha el audio adjunto y genera una transcripción altamente precisa. "
        "Identifica a los hablantes (Speaker A, Speaker B, etc.) y mantén la estructura de diálogo. "
        "Si el audio es en español, la transcripción debe ser en español."
    )

    response = model.generate_content([prompt, audio_file])
    
    # 4. Limpieza (opcional: borrar el archivo de Google AI después de procesarlo)
    # genai.delete_file(audio_file.name)

    return response.text

if __name__ == "__main__":
    # Prueba rápida si se ejecuta directamente
    import sys
    if len(sys.argv) > 1:
        resultado = transcribir_audio(sys.argv[1])
        if resultado:
            print("\n--- TRANSCRIPCIÓN FINAL ---")
            print(resultado)
    else:
        print("Uso: python scripts/transcripcion_gemini.py ruta/al/archivo.mp3")
