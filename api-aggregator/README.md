# api-aggregator

Two upstreams behind declarative pico-httpx clients, hardened with pico-resilience and pico-caching.

What to look at:

- `GeoApi`/`WeatherApi`: `@http_client` stubs; path placeholders and query params come from the method signature.
- `Geocoder.locate` is `@cacheable`: repeated briefings for the same city hit the geo upstream once.
- `BriefingService.briefing` combines `@retryable` (absorbs transient 503s) with `@circuit_breaker`. Retry attempts re-invoke the method directly, so the breaker counts one failure per request; after `failure_threshold` failing requests it opens and the upstream stops being called at all - the test asserts the transport call count stays frozen.
- Tests stub at the transport seam (`httpx.MockTransport`), never the application code.

```bash
pip install -e ".[dev]" && pytest
```
