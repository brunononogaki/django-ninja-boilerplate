#!/bin/bash

set -e

echo "Aguardando o banco de dados..."
python /app/infra/wait-for-postgres.py

echo "Executando migrations..."
python manage.py migrate

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando aplicação..."
exec "$@"
