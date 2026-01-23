#!/bin/bash
set -e

echo "Aguardando banco de dados..."
sleep 10

echo "Executando migrations..."
python manage.py migrate

echo "Iniciando servidor..."
python manage.py runserver 0.0.0.0:8000
