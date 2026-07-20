#!/usr/bin/env bash
# One-command deploy for a single cloud VM (Docker + Docker Compose installed).
#
#   Usage (on the VM, from the smarthr360-platform repo root):
#     cp deploy/prod/.env.prod.example deploy/prod/.env.prod   # edit it once
#     bash deploy/prod/deploy.sh
#
# Two modes:
#   (default)        pull the prebuilt images CI publishes to GHCR. Those are
#                    amd64, so this only works on an amd64 host.
#   DEPLOY_BUILD=1   build every service here instead. Required on arm64 hosts
#                    such as Oracle Cloud's Always Free Ampere A1 shape, where
#                    the published amd64 images will not run. The first build
#                    takes a while (future-skills carries the ML stack); later
#                    runs reuse the layer cache.
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

BACKENDS="auth core-hr workload retention career-sim future-skills policy-gen"

if [ "${DEPLOY_BUILD:-0}" = "1" ]; then
  echo "==> Building all service images on this host ($(uname -m))"
  # postgres/caddy come from Docker Hub and are already multi-arch.
  $COMPOSE pull postgres caddy
  # Compose tags each build with the image: name from the prod overlay, so the
  # locally built image is what `up` uses -- nothing is fetched from GHCR.
  $COMPOSE build $BACKENDS frontend
else
  if [ "$(uname -m)" != "x86_64" ]; then
    echo "!! This host is $(uname -m) but the GHCR images are amd64."
    echo "!! Re-run with DEPLOY_BUILD=1 to build them here instead."
    exit 1
  fi
  echo "==> Pulling prebuilt service images from GHCR"
  # Listed explicitly rather than pulling everything: the base compose gives
  # every service a build section, so --ignore-buildable would skip all of
  # them, and the frontend must not be pulled at all -- its NEXT_PUBLIC_* URLs
  # are baked in at build time and have to carry this deployment's DEMO_DOMAIN.
  $COMPOSE pull postgres caddy $BACKENDS

  echo "==> Building the frontend for ${DEMO_DOMAIN:-this domain}"
  $COMPOSE build frontend
fi

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
