#!/usr/bin/env bash
# One-command deploy for a single cloud VM (Docker + Docker Compose installed).
#
#   Usage (on the VM, from the smarthr360-platform repo root):
#     cp deploy/prod/.env.prod.example deploy/prod/.env.prod   # edit it once
#     bash deploy/prod/deploy.sh
#
# Idempotent: safe to re-run to ship an update.
set -euo pipefail

cd "$(dirname "$0")/../.."   # -> smarthr360-platform repo root

COMPOSE="docker compose --env-file deploy/prod/.env.prod \
  -f docker-compose.yml -f deploy/prod/docker-compose.prod.yml"

echo "==> Pulling latest source (with submodules)"
git pull --recurse-submodules || true
git submodule update --init --recursive

echo "==> Ensuring RS256 keys exist"
[ -f keys/jwt_private.pem ] || ./scripts/generate_rsa_keys.sh

echo "==> Pulling prebuilt service images from GHCR"
# The seven Django services come from their own CI. Listed explicitly rather
# than pulling everything: the base compose gives every service a build
# section, so --ignore-buildable would skip all of them, and the frontend must
# not be pulled at all -- its NEXT_PUBLIC_* URLs are baked in at build time and
# have to point at this deployment's DEMO_DOMAIN.
$COMPOSE pull postgres caddy auth core-hr workload retention career-sim future-skills policy-gen

echo "==> Building the frontend for ${DEMO_DOMAIN:-this domain}"
$COMPOSE build frontend

echo "==> Starting the stack behind Caddy"
$COMPOSE up -d

echo "==> Waiting for Postgres"
until $COMPOSE exec -T postgres pg_isready >/dev/null 2>&1; do sleep 2; done

echo "==> Running migrations"
for s in auth core-hr career-sim workload policy-gen retention future-skills; do
  $COMPOSE exec -T "$s" python manage.py migrate --noinput
done

echo "==> Seeding the demo dataset + read-only guest (idempotent)"
bash scripts/seed_demo.sh || $COMPOSE exec -T auth python manage.py seed_demo

echo "==> Done. Public demo: https://${DEMO_DOMAIN:-your-domain}"
echo "    Guest (read-only) and all demo credentials are in DEMO.md."
