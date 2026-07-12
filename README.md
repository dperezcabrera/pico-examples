# pico-examples

Non-trivial, runnable examples for the [pico ecosystem](https://github.com/dperezcabrera/pico-ioc). Each directory is a self-contained project with its own dependencies and a hermetic test suite: no broker, database server or network is needed to run any of them, yet the application code is exactly what you would deploy.

| Example | Shows | Modules |
|---|---|---|
| [order-service](order-service/) | REST CRUD, repository with derived queries, transactional rollback on business failure | fastapi, sqlalchemy |
| [api-aggregator](api-aggregator/) | Declarative HTTP clients, retry that absorbs flaky upstreams, circuit breaker failing fast, cached geocoding | fastapi, httpx, resilience, caching |
| [secure-notes](secure-notes/) | Embedded JWT issuer plus request validation: public reads, authenticated writes, role-gated deletes | fastapi, server-auth, client-auth |
| [worker-invoicing](worker-invoicing/) | DI-aware Celery tasks enqueued by an in-process scheduler | celery, scheduling |
| [observability-service](observability-service/) | Health indicators wired to business state, prometheus metrics scraped by a real Prometheus (compose), request traces | fastapi, actuator, otel |
| [runtime-config](runtime-config/) | Hot config reload through POST /actuator/refresh: resilience policies change without restart | fastapi, actuator, resilience |
| [dockerized-orders](dockerized-orders/) | The same service deployed: Docker Compose with Postgres and Redis, Kubernetes manifests with probes | fastapi, sqlalchemy, caching, data-redis, actuator |

## Running an example

```bash
cd order-service
pip install -e ".[dev]"
pytest
```

Tests run under [pico-testing](https://github.com/dperezcabrera/pico-testing): the package under test is declared once (`pico_module` in `pyproject.toml`) and containers are built with the `make_container`/`make_client` fixtures.

## The deployable example

`dockerized-orders` additionally ships a `Dockerfile`, a Compose stack and Kubernetes manifests. With Docker installed:

```bash
cd dockerized-orders
./smoke.sh
```

builds the image from PyPI packages, boots Postgres and Redis, places an order through the real stack and tears everything down.

## Conventions

- Application code lives in `src/<package>/app.py`; the deployable example adds an import-safe `main.py` factory (`uvicorn --factory`).
- Tests stub only infrastructure boundaries (HTTP transports, Redis, the JWKS fetch); the application wiring is never faked.
- Every failure path shown is asserted by a test: rollback really rolls back, the breaker really stops calling the upstream.

## License

MIT
