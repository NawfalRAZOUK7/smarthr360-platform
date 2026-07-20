# Deploying the public demo

The stack is eight services plus Postgres behind Caddy, which terminates TLS on
one public origin and path-routes to each service.

## Free-tier target: Oracle Cloud Always Free + sslip.io

Oracle's Always Free **Ampere A1** shape (4 OCPU / 24 GB) is the only free
option large enough for this stack, and `sslip.io` supplies a hostname with no
domain purchase. Total cost: nothing. Three things about that combination
change how you deploy.

### 1. Ampere A1 is arm64

CI publishes **amd64 and arm64** images, so Ampere can pull rather than compile.
The six lighter Django services emulate arm64 on an amd64 runner; future-skills
builds each architecture on its own native runner, because emulating its ML
stack turns a ~20 minute build into hours.

To pull, the images must be reachable from the VM — see §4.

Building on the VM instead stays available and needs no registry access at all:

```bash
DEPLOY_BUILD=1 bash deploy/prod/deploy.sh
```

That compiles all eight images locally. Expect 15–30 minutes on the first run;
later runs reuse the layer cache. It is the fallback when a pull is not
possible, and the images are verified to build natively on arm64.

### 2. Oracle blocks the ports twice

This is the most common way a deployment looks broken when it isn't. Opening the
**VCN Security List** is not enough — Oracle's Ubuntu images also block inbound
at the OS level with netfilter. Open both, or Caddy cannot answer the ACME
challenge and the failure reads like a certificate problem.

In the Console: instance → VCN → Security List → ingress rules for `0.0.0.0/0`
on TCP **80** and **443**. Then on the box:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 3. sslip.io works, but mind the certificate rate limit

`sslip.io` resolves any embedded IP with no DNS setup: with public IP
`140.238.1.2`, `smarthr360.140.238.1.2.sslip.io` already points at the box.
Caddy needs nothing special — set `DEMO_DOMAIN` and it requests a certificate
over HTTP-01/TLS-ALPN once 80 and 443 are reachable.

The catch: **`sslip.io` is not on the Public Suffix List**, so Let's Encrypt
counts every `*.sslip.io` certificate against a single registered domain, and
that global limit (50 per week) is often already exhausted by other users. If
issuance fails with *"too many certificates already issued"*, that is not a
misconfiguration on your side.

Caddy falls back to **ZeroSSL** automatically when Let's Encrypt refuses, which
usually resolves it. If both fail, a cheap real domain removes the problem for
good.

### 4. GHCR images are private by default

Packages published by Actions start **private even when the repository is
public**, so a pull from the VM fails with `denied` or `403 Forbidden` until you
choose one of:

- **Make them public** — for each package under
  <https://github.com/NawfalRAZOUK7?tab=packages>: Package settings → Change
  visibility → Public. Nothing else to configure afterwards.
- **Keep them private and authenticate** — create a PAT with `read:packages`,
  then on the VM:

  ```bash
  echo "$GHCR_PAT" | docker login ghcr.io -u NawfalRAZOUK7 --password-stdin
  ```

- **Skip the registry** — `DEPLOY_BUILD=1` builds locally and needs no access.

Seven packages are involved, one per backend service. The frontend is never
published: its NEXT_PUBLIC_* URLs are baked in at build time, so it is always
built on the VM against your DEMO_DOMAIN.

## First-time setup

1. **Instance** — Ubuntu 22.04, Ampere A1, 4 OCPU / 24 GB, boot volume ~100 GB.
   "Out of capacity" is common on the free ARM shape; retry or pick another
   availability domain.
2. **Ports** — both places, as above.
3. **Docker**

   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker ubuntu && exec sudo su - ubuntu
   ```

4. **Clone**

   ```bash
   git clone --recurse-submodules https://github.com/NawfalRAZOUK7/smarthr360-platform.git
   cd smarthr360-platform
   ```

5. **Configure** — copy the template and fill it in. `DEMO_DOMAIN`,
   `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` all take
   the sslip.io hostname (the last two with `https://`). Compose requires a
   separate signing key per service; the generator loop is in the file.

   ```bash
   cp deploy/prod/.env.prod.example deploy/prod/.env.prod
   ```

6. **Deploy** — build on the VM, which needs no registry access:

   ```bash
   DEPLOY_BUILD=1 bash deploy/prod/deploy.sh
   ```

   Once the images are reachable (§4), dropping `DEPLOY_BUILD=1` pulls them
   instead and cuts the deploy to a couple of minutes.

7. **Visit** `https://smarthr360.<ip>.sslip.io` — the read-only guest demo.

## Deploying afterwards from GitHub

Add four repository secrets so the **Deploy** workflow can reach the box:
`DEPLOY_HOST` (public IP), `DEPLOY_USER` (`ubuntu`), `DEPLOY_SSH_KEY` (private
key), `DEPLOY_PATH` (`/home/ubuntu/smarthr360-platform`). Optionally set the
`DEMO_URL` variable so the workflow verifies the public URL answers afterwards.

Then deployment is *Actions → Deploy → Run workflow*. Set `DEPLOY_BUILD=1` in
the environment on the VM side for an arm64 host.

## Troubleshooting

**`auth` exits with `PermissionError: /run/secrets/jwt_private.pem`.**
`generate_rsa_keys.sh` writes the key `0600` owned by the deploying user, while
services run as uid 10001 and read it through a bind-mounted compose secret. On
Linux the container sees the real owner and cannot read it. Docker Desktop on
macOS remaps ownership, so this never reproduces locally. Make the key readable
by the service user, or run the stack as the key's owner.

**Certificate never issues.** Check both firewalls first (§2), then the rate
limit (§3). `docker compose logs caddy` states which.

**`exec format error`.** amd64 images on an arm64 host — use `DEPLOY_BUILD=1`.

**LLM panels are empty.** Set `GROQ_API_KEY` in `.env.prod`; the demo runs
without it, but policy generation returns nothing.
