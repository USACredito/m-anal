# Usar imagen de Python ligera
FROM python:3.12-slim

# Evitar que Python genere archivos .pyc y habilitar salida de log
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias + cron
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar la cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear directorio temporal si no existe
RUN mkdir -p .tmp

# Dar permisos de ejecución al script de arranque
RUN chmod +x start.sh

# Exponer el puerto del Dashboard
EXPOSE 5050

# Usar el script de inicio personalizado para manejar Cron + Dashboard
CMD ["/bin/bash", "./start.sh"]
