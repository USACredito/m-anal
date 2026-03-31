#!/bin/bash

# 1. Crear el archivo de cron (cada hora en el minuto 0)
# Usamos variables de entorno para que cron sepa dónde buscar python
echo "0 * * * * cd /app && /usr/local/bin/python main.py --semana >> /app/.tmp/cron_log.txt 2>&1" > /etc/cron.d/analisis-cron

# 2. Dar permisos al archivo de cron
chmod 0644 /etc/cron.d/analisis-cron

# 3. Aplicar el cronjob
crontab /etc/cron.d/analisis-cron

# 4. Iniciar el demonio de cron en segundo plano
service cron start

echo "SISTEMA DE ANÁLISIS AUTOMÁTICO INICIADO"
echo "Dashboard: http://0.0.0.0:5050"
echo "Cron: Ejecutando main.py cada hora."

# 5. Iniciar el Dashboard como proceso principal (mantiene el contenedor vivo)
exec python dashboard/app.py
