# TCG Marketplace Platform Demo

Production-shaped DevOps demo: operating a trading-card marketplace API the way an SRE would.
Built to mirror a real marketplace stack: **AWS · EKS · Helm · Terraform · GitLab CI · Prometheus/Grafana/Alertmanager · Loki structured logging · MySQL · Redis · Cloudflare WAF-as-code**.

> Config management: I use **Ansible** in my day-to-day work (playbooks in my other repos); Puppet concepts map 1:1.

## What this demonstrates

| Capability | Where |
|---|---|
| Marketplace workload (card catalog + price API) | `app/` — FastAPI, MySQL, Redis cache with TTL |
| CI/CD with GitLab CI | `.gitlab-ci.yml` — lint → test → build → scan → deploy |
| Infrastructure as Code | `terraform/` — VPC, EKS, ECR (eu-central-1) |
| Kubernetes in production style | `helm/tcg-marketplace/` — own chart, HPA, probes, PDB |
| Monitoring & alerting | `observability/prometheus/` — SLO-style alerts (p95 latency, cache hit-rate, MySQL health) |
| Logging architecture | `observability/loki/` + `docs/LOGGING.md` — structured JSON logs, Promtail → Loki, retention & label design |
| Edge security as code | `cloudflare/` — WAF + rate-limiting rules in Terraform (plan-only) |

## Architecture

```
Client ──> Cloudflare (WAF, rate limiting)          [defined as code, plan-only]
              │
              ▼
        ALB Ingress ──> EKS: tcg-marketplace (FastAPI)
                              │            │
                        MySQL (catalog)  Redis (price cache, TTL 60s)
                              │
              Promtail ──> Loki   Prometheus ──> Alertmanager
                        └──────── Grafana ────────┘
```

MySQL and Redis run **in-cluster via Helm** to keep demo cost near zero; `docs/ARCHITECTURE.md` explains why production would use RDS + ElastiCache instead (backups, failover, maintenance windows).

## Run locally

```bash
docker compose up --build
curl localhost:8000/cards/search?q=charizard
curl localhost:8000/cards/1/price     # second call is a Redis cache hit
open http://localhost:3000            # Grafana (dashboards pre-provisioned)
```

## Deploy to AWS

```bash
cd terraform/envs/dev && terraform init && terraform apply
helm upgrade --install tcg helm/tcg-marketplace -n marketplace --create-namespace
```

## Repo layout

```
app/            FastAPI service, Dockerfile, tests
helm/           Helm chart (deployment, service, ingress, HPA, PDB, servicemonitor)
terraform/      AWS infra (modules + dev env), Cloudflare provider (separate dir)
observability/  Prometheus rules, Alertmanager routes, Grafana dashboards, Loki/Promtail
cloudflare/     WAF & rate-limit rules as Terraform (plan-only, documented)
docs/           LOGGING.md (logging architecture design), ARCHITECTURE.md
.gitlab-ci.yml  Full pipeline
```
