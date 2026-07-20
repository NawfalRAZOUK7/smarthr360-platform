# Local HTTPS parity (mkcert + Caddy)

Runs the whole stack over **HTTPS locally** so it matches production: the
browser talks TLS, cookies are `Secure`, and mixed-content / cross-origin
issues surface on your machine instead of in prod. A Caddy reverse proxy
terminates TLS (with mkcert-issued, OS-trusted certs) and forwards to each
service on the compose network.

> Heads-up: this overlay changes browser-facing URLs and needs a frontend
> rebuild. It's additive — the plain-HTTP stack still works without it.

## One-time setup

**1. Install mkcert and its local CA** (macOS):

```bash
brew install mkcert nss   # nss = Firefox trust
mkcert -install           # adds mkcert's root CA to the system trust store
```

**2. Generate the cert** into `deploy/local-https/certs/`:

```bash
cd ~/Smarthr360/smarthr360-platform/deploy/local-https
mkdir -p certs
mkcert -cert-file certs/smarthr360.pem -key-file certs/smarthr360-key.pem \
  app.smarthr360.local \
  auth.smarthr360.local corehr.smarthr360.local careersim.smarthr360.local \
  futureskills.smarthr360.local workload.smarthr360.local \
  policygen.smarthr360.local retention.smarthr360.local
```

**3. Map the hostnames** to loopback in `/etc/hosts`:

```bash
sudo tee -a /etc/hosts >/dev/null <<'EOF'
127.0.0.1 app.smarthr360.local auth.smarthr360.local corehr.smarthr360.local careersim.smarthr360.local futureskills.smarthr360.local workload.smarthr360.local policygen.smarthr360.local retention.smarthr360.local
EOF
```

## Run

From the platform root, layer the overlay on top of the base compose (the
frontend rebuild bakes in the HTTPS `NEXT_PUBLIC_*` URLs):

```bash
cd ~/Smarthr360/smarthr360-platform
docker compose -f docker-compose.yml -f deploy/local-https/docker-compose.https.yml up -d --build frontend caddy
docker compose -f docker-compose.yml -f deploy/local-https/docker-compose.https.yml up -d
```

Then open **https://app.smarthr360.local** — green padlock, no warnings.

## What it validates that plain HTTP doesn't

- `Secure` cookies actually round-trip (they're dropped over HTTP).
- CORS against a real cross-origin HTTPS origin.
- Any hardcoded `http://` URLs / mixed-content get caught by the browser.
- The reverse-proxy + `X-Forwarded-Proto` path you'll use in production.

## Notes / caveats

- **I could not test this overlay end-to-end from the build environment** — it
  depends on your machine's trust store, `/etc/hosts`, and a frontend rebuild.
  The files are correct by construction; validate with the steps above.
- To also enforce Django's production security flags behind this proxy, set
  `DJANGO_SETTINGS_MODULE=config.settings.production` per service and add
  `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")` (see
  `deploy/HARDENING.md`). Caddy sets `X-Forwarded-Proto: https` automatically.
- Revert by simply omitting the `-f deploy/local-https/...` overlay and
  rebuilding the frontend on the plain-HTTP args.
