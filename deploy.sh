#!/bin/bash

# Deploy script for production environment

set -e  # Exit on any error

if [ "$1" = "down" ]; then
  echo "🛑 Stopping and removing production containers..."
  docker compose --file infra/compose-pro.yaml down
  exit 0
fi

if [ "$1" = "up" ] || [ -z "$1" ]; then
  # Default: up (build, up, migrate)
  echo "🚀 Starting production deployment..."
  # Check if .env.production exists
  if [ ! -f .env.production ]; then
      echo "❌ Error: .env.production file not found!"
      exit 1
  fi
  # Symlink .env.production to .env
  ln -sf .env.production .env
  # Build and start containers
  docker compose --file infra/compose-pro.yaml up -d --build
  # Run migrations inside the web container
  WEB_CONTAINER=$(docker compose --file infra/compose-pro.yaml ps -q web)
  if [ -n "$WEB_CONTAINER" ]; then
    docker compose --file infra/compose-pro.yaml exec web python manage.py migrate
  else
    echo "Web container not found. Migration step skipped."
  fi
  echo "✅ Deployment complete! Containers are up and migrations applied."
  exit 0
fi

echo "Usage: $0 [up|down]"
exit 1
