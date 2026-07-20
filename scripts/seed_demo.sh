#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

services=(auth core-hr career-sim workload policy-gen retention future-skills)

# Services that are not currently running are skipped with a WARN rather than
# aborting the whole seed. Heavy services (notably future-skills) are routinely
# excluded from local bring-ups, and a hard failure there would otherwise mask a
# successful seed of everything else.
running="$(docker compose ps --services --filter status=running)"

# Plain strings rather than arrays: macOS ships bash 3.2, where expanding an
# empty array under `set -u` is an "unbound variable" error.
seeded=""
skipped=""
failed=""

for service in "${services[@]}"; do
  if ! grep -qx "${service}" <<<"${running}"; then
    echo "WARN: skipping ${service} (not running)"
    skipped="${skipped} ${service}"
    continue
  fi

  echo "==> Migrating ${service}"
  if ! docker compose exec -T "${service}" python manage.py migrate --noinput; then
    echo "WARN: migrate failed for ${service}"
    failed="${failed} ${service}"
    continue
  fi

  echo "==> Seeding ${service}"
  if ! docker compose exec -T "${service}" python manage.py seed_demo; then
    echo "WARN: seed failed for ${service}"
    failed="${failed} ${service}"
    continue
  fi

  seeded="${seeded} ${service}"
done

echo
echo "Seeded: ${seeded:-(none)}"
echo "Skipped:${skipped:-  (none)}"
echo "Failed: ${failed:-(none)}"

if [ -n "${failed}" ]; then
  echo "Seed completed with failures. See DEMO.md for accounts and story paths."
  exit 1
fi

echo "Demo data is ready. See DEMO.md for accounts and story paths."
