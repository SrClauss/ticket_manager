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
ssh root@82.25.69.42 "cd /srv/ticket_manager && git pull --quiet && docker compose pull && docker compose up -d --remove-orphans --build"

echo "Done."
