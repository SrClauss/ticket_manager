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

echo "ok"
#!/usr/bin/env bash
set -euo pipefail

MSG="${1:-Deploy: automatic deploy from script}"

# Commit and push local changes
git add -A
if ! git diff --staged --quiet; then
  git commit -m "$MSG" || git commit --allow-empty -m "$MSG"
else
  # no staged changes - still create an empty commit to mark deploy
  git commit --allow-empty -m "$MSG" || true
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD || echo "HEAD")

echo "Pushing branch $BRANCH to origin..."
git push origin "$BRANCH" || {
  echo "git push failed" >&2
}

# Remote deploy
SSH_TARGET="root@129.121.32.101"
REMOTE_DIR="/srv/ticket_manager"
# use port 22022 for SSH connections
SSH_OPTS="-p 22022 -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "Attempting remote deploy to $SSH_TARGET:$REMOTE_DIR"
ssh $SSH_OPTS "$SSH_TARGET" "set -euo pipefail; cd $REMOTE_DIR || (echo 'remote dir missing' && exit 1); git pull origin $BRANCH || true; docker compose pull --quiet || true; docker compose up -d --build || true; if [ -x ./start.sh ]; then ./start.sh || true; fi"

if [ $? -eq 0 ]; then
  echo "Remote deploy command completed (may have warnings)."
else
  echo "Remote deploy encountered errors or SSH not available. See above output." >&2
fi
