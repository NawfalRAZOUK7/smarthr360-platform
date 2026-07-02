# SmartHR360 — k3s deployment

Target: single VPS (≥4 GB RAM) running [k3s](https://k3s.io) (ADR-006).

## One-time setup

```bash
# on the VPS
curl -sfL https://get.k3s.io | sh -            # k3s + traefik ingress
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# namespace + secrets (from your workstation, KUBECONFIG pointing at the VPS)
kubectl apply -f namespace.yaml
kubectl -n smarthr360 create secret generic jwt-keys \
  --from-file=jwt_private.pem=../../keys/jwt_private.pem \
  --from-file=jwt_public.pem=../../keys/jwt_public.pem
kubectl -n smarthr360 create secret generic app-secrets \
  --from-literal=POSTGRES_PASSWORD='<strong-password>' \
  --from-literal=AUTH_SECRET_KEY='<random-50-chars>' \
  --from-literal=CORE_HR_SECRET_KEY='<random-50-chars>' \
  --from-literal=CAREER_SIM_SECRET_KEY='<random-50-chars>' \
  --from-literal=WORKLOAD_SECRET_KEY='<random-50-chars>' \
  --from-literal=POLICY_GEN_SECRET_KEY='<random-50-chars>' \
  --from-literal=RETENTION_SECRET_KEY='<random-50-chars>'
kubectl apply -f cluster-issuer.yaml           # edit email first
```

## Deploy / upgrade

Images come from GHCR (built by each repo's CI). Set the tag in
`kustomization.yaml`, then:

```bash
kubectl apply -k .
kubectl -n smarthr360 get pods -w
```

## Layout

| File | Contents |
|---|---|
| `namespace.yaml` | `smarthr360` namespace |
| `postgres.yaml` | StatefulSet + PVC + per-service DB init |
| `auth.yaml` | Deployment/Service — mounts private+public key |
| `core-hr.yaml` `career-sim.yaml` `future-skills.yaml` | Deployment/Service — public key only |
| `ingress.yaml` | Traefik ingress, TLS via cert-manager, host routing |
| `cluster-issuer.yaml` | Let's Encrypt issuer |
| `kustomization.yaml` | ties it together, image tags pinned here |

Probes hit each service's `/healthz/`. Every Deployment sets resource
requests/limits sized for a 4 GB node.
