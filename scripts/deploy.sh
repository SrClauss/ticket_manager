#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 \"mensagem de commit\""
  exit 1
fi

COMMIT_MSG="$1"

echo "Stagging changes..."
git add -A

echo "Committing..."
if git commit -m "$COMMIT_MSG"; then
  echo "Committed."
else
  echo "No changes to commit."
fi

echo "Pushing..."
git push --quiet

echo "Deploying to server..."
ssh root@82.25.69.42 << 'SSH'
set -euo pipefail
cd /srv/ticket_manager
echo "- git pull"
git pull --quiet

echo "- pulling images"
docker compose pull || true

echo "- building fastapi image (this will run Tailwind build via Dockerfile builder)"
docker compose build --pull fastapi

echo "- bringing up containers"
docker compose up -d --remove-orphans --build

# verify tailwind.css exists inside the fastapi container filesystem
echo "- verifying built CSS"
if docker compose exec -T fastapi test -f /app/app/static/css/tailwind.css; then
  echo "tailwind.css present"
else
  echo "WARNING: tailwind.css not found in container at /app/app/static/css/tailwind.css"
  echo "You may need to run 'docker compose build --no-cache fastapi' or ensure Tailwind build step succeeded."
  exit 2
fi

SSH

echo "ok"
