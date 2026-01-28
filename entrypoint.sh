#!/bin/bash
set -e

echo "Aguardando banco de dados..."
sleep 10

echo "Executando migrations..."
python manage.py migrate

echo "Iniciando servidor..."
uvicorn safetodo.asgi:application --host 0.0.0.0 --port 8000
