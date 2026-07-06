# Architecture Notes

## Demo vs production trade-offs (deliberate, documented)

| Component | Demo choice | Production choice | Why the demo differs |
|---|---|---|---|
| MySQL | In-cluster (Helm) | RDS MySQL Multi-AZ | Cost. RDS buys backups, failover, patching windows. |
| Redis | In-cluster (Helm) | ElastiCache | Same: managed failover + maintenance. |
| Nodes | 2x t3.medium SPOT | Mixed on-demand base + spot burst | Spot interruption is acceptable for a demo, not for checkout. |
| NAT | Single NAT gateway | One per AZ | ~€32/mo per NAT; demo tolerates the AZ-failure risk. |
| TLS/Ingress | Skipped locally | ALB + ACM + cert-manager | Out of demo scope. |
| Secrets | K8s Secret | External Secrets Operator + AWS Secrets Manager | Demonstrated in lemon-brokerage-platform-demo. |

## Scaling story (interview talking points)

- Read path is cache-first: search and price lookups hit Redis; MySQL sees cache misses only.
  Alert exists for hit-rate < 80% because that is the leading indicator of DB overload.
- HPA on CPU for the stateless API; MySQL scales vertically first, then read replicas.
- Cloudflare absorbs scraper traffic before it reaches the ALB (see cloudflare/).
