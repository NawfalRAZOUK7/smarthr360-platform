#!/usr/bin/env bash
# Generate the RS256 keypair for SmartHR360 JWT signing.
#   private key -> keys/jwt_private.pem   (SECRET: only smarthr360-auth gets it, NEVER commit)
#   public key  -> keys/jwt_public.pem    (safe to commit/distribute to all services)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/keys"
mkdir -p "$DIR"

if [[ -f "$DIR/jwt_private.pem" ]]; then
  echo "keys already exist in $DIR — refusing to overwrite." >&2
  exit 1
fi

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$DIR/jwt_private.pem"
openssl pkey -in "$DIR/jwt_private.pem" -pubout -out "$DIR/jwt_public.pem"
chmod 600 "$DIR/jwt_private.pem"

echo "OK:"
echo "  $DIR/jwt_private.pem  (secret — auth service only)"
echo "  $DIR/jwt_public.pem   (distribute to all services)"
