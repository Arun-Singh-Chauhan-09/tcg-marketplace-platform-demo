# Logging Architecture

Design notes for the logging pipeline in this demo, and how it would scale for a real marketplace.

## Goals

1. **Debuggable in minutes** — an on-call engineer should go from alert → offending request logs in under 5 minutes.
2. **Cheap at volume** — a marketplace serving millions of card searches/day cannot afford to index every log line like a database.
3. **Structured from the source** — parsing free-text logs at query time is where logging architectures go to die.

## Design

```
FastAPI app ──stdout (JSON)──> Promtail ──push──> Loki ──query──> Grafana
                                   │
                             label extraction
                          (level, service only)
```

### Decisions and why

| Decision | Rationale |
|---|---|
| **JSON to stdout, nothing else** | 12-factor; the app never knows where logs go. Swap Loki for ELK/CloudWatch without touching app code. |
| **Loki over Elasticsearch** | Loki indexes only labels, not content — ~10x cheaper at marketplace volume. Full-text needs are served by LogQL filtering at query time, which is fine for debugging workflows. |
| **Low-cardinality labels only** (`level`, `service`, `container`) | The classic Loki failure mode is labeling by `user_id` or `card_id` → index explosion. High-cardinality fields stay in the JSON body and are filtered with `| json | card_id="123"`. |
| **7-day hot retention (demo)** | Production tiering: 7d in Loki (debugging), 90d in S3 via Loki's object storage (compliance/incident review), lifecycle-expire after that. |
| **Request logs include `duration_ms`, `status`, `path`** | Lets logs answer "which requests were slow" when metrics only say "something is slow". Logs and metrics share label names so you can pivot between them in Grafana. |

### What I'd add for production

- **Trace correlation**: inject a `trace_id` per request (OpenTelemetry — implemented in my lemon-brokerage-platform-demo repo) so a Grafana log line links to its distributed trace.
- **Audit log stream**: seller account changes and payout events go to a separate, longer-retention, append-only stream (S3 + Object Lock) — distinct from debug logs.
- **PII policy**: buyer emails/addresses never enter logs; enforced by a Promtail pipeline stage that drops known PII fields as a safety net, with the primary control in code review.
- **Per-team log volumes**: Loki multi-tenancy or per-namespace labels so one noisy service can't blow the retention budget for everyone.

## Alternatives considered

- **ELK/OpenSearch**: better full-text search, significantly higher operational and storage cost. Right choice if search-heavy compliance queries dominate; wrong default for debugging-driven logging.
- **CloudWatch Logs only**: simplest on AWS, but query ergonomics (Insights) and cross-service dashboards are weaker, and cost grows sharply with volume.
