#!/usr/bin/env bash
set -euo pipefail

# deploy_remote.sh - deploy via SSH (remote host defaults can be overridden)
# Usage: deploy_remote.sh "commit message" [ssh_target] [ssh_port]
# Example: ./scripts/deploy_remote.sh "Hotfix" root@129.121.32.101 22022

if [ $# -lt 1 ]; then
  echo "Uso: $0 \"mensagem de commit\" [ssh_target] [ssh_port]"
  exit 1
fi

COMMIT_MSG="$1"
SSH_TARGET="${2:-root@129.121.32.101}"
SSH_PORT="${3:-22022}"

SSH_OPTS="-p ${SSH_PORT} -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "Staging changes..."
git add -A

echo "Committing..."
if git commit -m "$COMMIT_MSG"; then
  echo "Committed."
else
  echo "No changes to commit."
fi

echo "Pushing..."
git push --quiet

echo "Deploying to ${SSH_TARGET} (port ${SSH_PORT})..."
ssh ${SSH_OPTS} "${SSH_TARGET}" bash -s << 'SSH'
set -euo pipefail
cd /srv/ticket_manager || exit 2
echo "- git pull"
git pull --quiet

echo "- pulling images"
docker compose pull || true

echo "- building fastapi image"
docker compose build --pull fastapi || true

echo "- bringing up containers"
docker compose up -d --remove-orphans --build

echo "- verifying built assets"
if docker compose exec -T fastapi test -f /app/app/static/css/tailwind.css; then
  echo "tailwind.css present"
else
  echo "WARNING: tailwind.css not found in container at /app/app/static/css/tailwind.css"
fi

SSH

echo "Remote deploy command completed (may have warnings)."
