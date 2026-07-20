#!/usr/bin/env bash
# gen_secret.sh — print one cryptographically-random secret to stdout.
#
#   usage: ./scripts/gen_secret.sh [length]   (default 50)
#
# Used by bootstrap.sh to fill .env dynamically; safe to use standalone:
#   AUTH_SECRET_KEY="$(./scripts/gen_secret.sh)"
set -euo pipefail

LENGTH="${1:-50}"

if command -v openssl >/dev/null 2>&1; then
  # base64 is ~4/3 chars per byte; generate extra then trim.
  openssl rand -base64 $((LENGTH * 2)) | tr -dc 'A-Za-z0-9' | head -c "$LENGTH"
elif command -v python3 >/dev/null 2>&1; then
  python3 - "$LENGTH" <<'PY'
import secrets, string, sys
n = int(sys.argv[1])
alphabet = string.ascii_letters + string.digits
print("".join(secrets.choice(alphabet) for _ in range(n)), end="")
PY
else
  # /dev/urandom fallback
  LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$LENGTH"
fi
echo
