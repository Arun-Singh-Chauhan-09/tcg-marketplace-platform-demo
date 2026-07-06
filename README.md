# TCG Marketplace Platform Demo

Production-shaped DevOps demo: operating a trading-card marketplace API the way an SRE would.
Built to mirror a real marketplace stack — **AWS · EKS · Helm · Terraform · GitLab CI · Prometheus/Grafana/Alertmanager · Loki structured logging · MySQL · Redis · Cloudflare WAF-as-code**.

> **Config management:** I use **Ansible** day-to-day (playbooks in my other repos). Puppet concepts map 1:1.

---

## Why this exists

This repo demonstrates the operational skills needed to run a high-traffic, read-heavy marketplace: fast cached lookups, a solid CI/CD pipeline, security scanning, infrastructure as code, and a monitoring + logging story an on-call engineer can actually use. Rather than a toy, every piece is shaped like a scaled-down version of the real thing.

The workload is a card catalog and price API — the read-heavy core of a marketplace where the same cards get searched and priced constantly, so caching and reliability matter.

---

## What this demonstrates

| Capability | Where |
|---|---|
| Marketplace workload (card catalog + price API) | `app/` — FastAPI, MySQL, Redis cache with TTL |
| CI/CD with GitLab CI | `.gitlab-ci.yml` — lint → test → build → scan → validate-infra → deploy |
| Infrastructure as Code | `terraform/` — VPC, EKS, ECR (eu-central-1) |
| Kubernetes in production style | `helm/tcg-marketplace/` — own chart, HPA, probes, PDB, ServiceMonitor |
| Monitoring & alerting | `observability/prometheus/` — SLO-style alerts (p95 latency, cache hit-rate, MySQL health) |
| Logging architecture | `observability/loki/` + `docs/LOGGING.md` — structured JSON logs, Promtail → Loki, retention & label design |
| Edge security as code | `cloudflare/` — WAF + rate-limiting rules in Terraform (plan-only) |

---

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

### Request flow

```
GET /cards/search?q=charizard
   └─> MySQL: SELECT ... WHERE name LIKE '%charizard%'   ──> results

GET /cards/1/price
   └─> Redis: is "price:1" cached?
         ├─ HIT  ─> return cached JSON            {"cache":"hit"}   (no DB touch)
         └─ MISS ─> MySQL read ─> write to Redis (TTL 60s)
                    return JSON                    {"cache":"miss"}
```

The cache absorbs repeat reads so MySQL only ever sees cache misses — the core scaling pattern for a read-heavy marketplace. A Prometheus alert fires if the cache hit-rate drops below 80%, because that's the leading indicator of the database taking load it shouldn't.

---

## Run locally

The full stack runs on one machine via Docker Compose:

```bash
docker compose up --build

# search hits MySQL
curl "localhost:8000/cards/search?q=charizard"

# first price call is a cache MISS (reads MySQL, writes Redis)
curl "localhost:8000/cards/1/price"

# second call within 60s is a cache HIT (served from Redis)
curl "localhost:8000/cards/1/price"

# Grafana (anonymous admin, datasources pre-provisioned)
open http://localhost:3000
```

Services started: `app`, `mysql`, `redis`, `prometheus`, `alertmanager`, `grafana`, `loki`, `promtail`.

Verify the observability chain:

```bash
# custom cache metrics in Prometheus
curl -s "localhost:9090/api/v1/query?query=price_cache_hits_total"

# app's structured JSON logs ingested by Loki
curl -s "localhost:3100/loki/api/v1/query?query=%7Bservice%3D%22tcg-marketplace%22%7D"
```

---

## CI/CD pipeline

Every push to `main` runs the full pipeline on GitLab CI shared runners:

```
lint ──────────► ruff (python) · helm lint · hadolint (Dockerfile)
   ▼
test ──────────► pytest against live MySQL + Redis service containers
   │              (proves the cache miss→hit path in CI, not just locally)
   ▼
build ─────────► Kaniko builds the image and pushes to the GitLab registry
   ▼
scan ──────────► Trivy scans the image for CVEs   [reports as warning]
   ▼
validate-infra ► terraform validate · cloudflare validate
   ▼
deploy ────────► helm upgrade → EKS               [manual gate, needs AWS]
```

**Deliberate policy choices:**

- **Trivy is non-blocking** (`allow_failure: true`). It scans every image and surfaces CVEs as a pipeline warning rather than failing the build. This is a demo-appropriate choice — in production, HIGH/CRITICAL findings would block the deploy and be remediated via dependency bumps or base-image updates.
- **Image builds use Kaniko** rather than docker-in-docker, so no privileged runner is required.
- **`deploy:dev` is a manual gate.** It's defined and validated but never auto-runs, so the demo never provisions a live cluster.

---

## What runs where (scope)

To be precise about what's live versus what's blueprint:

| Layer | State | Notes |
|---|---|---|
| **App + MySQL + Redis + full observability** | **Runs locally** via `docker compose` | The only place anything actually executes. Cache miss→hit, metrics, and structured logs are all demonstrable here. |
| **CI pipeline** (lint · test · build · scan · validate-infra) | **Runs on GitLab CI** | Tests exercise the real cache path against live MySQL+Redis service containers. |
| **Terraform (EKS/VPC/RDS) + Helm** | **Validated, not applied** | CI runs `terraform validate` only — it checks syntax, it does **not** call `terraform apply`, so **no AWS resources are created and nothing incurs cloud cost.** |
| **`deploy:dev`** | **Manual gate, never triggered** | Gated behind `when: manual` + AWS credentials. Shows the deploy path without provisioning a live cluster. |

**Honest note on the Terraform modules:** `terraform/modules/network` and `modules/eks` are intentionally kept as skeletons here to stay within demo scope. They validate cleanly but are not yet complete enough to `apply` into a working cluster — the full working patterns live in my `lemon-brokerage-platform-demo` repo and would be ported in for a real deployment.

---

## Deploy to AWS (not run in this demo)

The path is defined and validated in CI, but applying it provisions a live EKS cluster (and cost), so it's left as a manual step:

```bash
cd terraform/envs/dev && terraform init && terraform apply
helm upgrade --install tcg helm/tcg-marketplace -n marketplace --create-namespace
```

---

## Observability details

- **Metrics** — the app exposes `/metrics` with custom counters (`price_cache_hits_total`, `price_cache_misses_total`) and a request-latency histogram. Prometheus scrapes it; Grafana visualises it.
- **Alerts** — marketplace-flavoured SLO rules in `observability/prometheus/alerts.yml`: price-API p95 latency > 300ms, cache hit-rate < 80%, search 5xx rate > 2%, and target-down.
- **Logs** — the app emits structured JSON to stdout. Promtail ships it to Loki, promoting only low-cardinality fields (`level`, `service`) to labels. The full design rationale, including why Loki over Elasticsearch and how retention would tier in production, is in [`docs/LOGGING.md`](docs/LOGGING.md).

---

## Repo layout

```
app/            FastAPI service, Dockerfile, tests, seed SQL
helm/           Helm chart (deployment, service, HPA, PDB, ServiceMonitor)
terraform/      AWS infra (modules + dev env)
cloudflare/     WAF & rate-limit rules as Terraform (plan-only)
observability/  Prometheus rules, Alertmanager routes, Grafana provisioning, Loki/Promtail
docs/           LOGGING.md (logging design), ARCHITECTURE.md (demo vs prod trade-offs)
docker-compose.yml   Local full-stack runner
.gitlab-ci.yml       Full pipeline
```

---

## Design trade-offs

Deliberate demo-vs-production choices (backups, failover, cost) are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — for example, running MySQL/Redis in-cluster here versus RDS + ElastiCache in production, and a single NAT gateway versus one per availability zone.

---

## Tech stack

**Runtime:** FastAPI (Python 3.12), MySQL 8.4, Redis 7
**Infra:** Terraform, AWS (EKS, VPC, ECR), Helm, Kubernetes
**CI/CD:** GitLab CI, Kaniko, Trivy, ruff, hadolint
**Observability:** Prometheus, Grafana, Alertmanager, Loki, Promtail
**Edge:** Cloudflare WAF + rate limiting (Terraform)