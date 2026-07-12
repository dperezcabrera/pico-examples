# observability-service

A service that tells you how it feels: actuator endpoints, health wired to business state, business metrics and request traces.

What to look at:

- `QueueHealth`: a health indicator that turns `/actuator/health` DOWN (HTTP 503) when the intake queue saturates, BEFORE requests start failing - that is what load balancer probes should see.
- `BuildInfo`: an info contributor merged into `/actuator/info`.
- `JOBS_ACCEPTED`: a plain prometheus counter on the default registry - the shared contract between pico-otel and `/actuator/metrics`.
- The trace test captures real request spans with an in-memory exporter.

```bash
pip install -e ".[dev]" && pytest   # hermetic suite
./smoke.sh                          # compose: a REAL Prometheus scrapes the app
```

## The monitoring contract, end to end

`docker-compose.yml` boots the app plus a real Prometheus configured to scrape `/actuator/metrics` (`prometheus.yml`). `smoke.sh` submits jobs and then asserts `jobs_accepted_total` through Prometheus' query API - validating the full chain: business code increments a counter on the default registry, pico-actuator serves it, Prometheus scrapes it, dashboards can query it.
