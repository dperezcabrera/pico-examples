# dockerized-orders

The deployable example: the same order service running against real Postgres and Redis under Docker Compose, with Kubernetes manifests included.

What to look at:

- `main.py`: import-safe factory (`uvicorn --factory dockerized_orders.main:create_app`); config comes from a YAML file selected by `CONFIG_PATH`, so image and environment stay decoupled.
- `Dockerfile`: the container healthcheck hits `/actuator/health` - the same endpoint the Kubernetes readiness and liveness probes use in `k8s/deployment.yaml`.
- `Catalog.price_cents` is `@cacheable` with pico-data-redis installed: every replica shares the price cache through Redis.
- Tests are hermetic (sqlite plus fakeredis); `smoke.sh` is the real thing.

```bash
pip install -e ".[dev]" && pytest   # hermetic suite
./smoke.sh                          # compose: build, boot, order, tear down
kubectl apply -f k8s/               # manifests (ConfigMap, Deployment, Service)
```
