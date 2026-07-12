import httpx
import pytest

from api_aggregator.app import GeoApi, WeatherApi

CONFIG = {
    "fastapi": {"title": "aggregator"},
    "resilience": {"enabled": True},
    "caching": {"enabled": True},
    "http": {
        "clients": {
            "geo": {"base_url": "https://geo.internal"},
            "weather": {"base_url": "https://weather.internal"},
        }
    },
}


@pytest.fixture
def harness(make_container, make_client):
    """Container + TestClient with both upstreams mocked at the transport seam."""
    container = make_container(
        "pico_fastapi", "pico_httpx", "pico_resilience", "pico_caching", "pico_ioc.event_bus", config=CONFIG
    )
    calls = {"geo": 0, "weather": 0, "weather_failures_left": 0}

    def geo_handler(request):
        calls["geo"] += 1
        return httpx.Response(200, json={"lat": 40.4, "lon": -3.7})

    def weather_handler(request):
        calls["weather"] += 1
        if calls["weather_failures_left"] > 0:
            calls["weather_failures_left"] -= 1
            return httpx.Response(503, json={"detail": "busy"})
        return httpx.Response(200, json={"summary": "sunny"})

    for api, handler, base in ((GeoApi, geo_handler, "https://geo.internal"), (WeatherApi, weather_handler, "https://weather.internal")):
        instance = container.get(api)
        instance.__dict__["_pico_httpx_aclient"] = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url=base
        )
    return make_client(container), calls


def test_briefing_aggregates_both_upstreams(harness):
    client, calls = harness
    r = client.get("/api/v1/briefing/madrid")
    assert r.status_code == 200, r.text
    assert r.json() == {"city": "madrid", "coords": [40.4, -3.7], "forecast": "sunny"}
    assert calls == {"geo": 1, "weather": 1, "weather_failures_left": 0}


def test_retry_absorbs_flaky_upstream(harness):
    client, calls = harness
    calls["weather_failures_left"] = 2
    r = client.get("/api/v1/briefing/madrid")
    assert r.status_code == 200
    assert calls["weather"] == 3  # 2 failures + 1 success, invisible to the caller


def test_geocoder_cache_hits_geo_once(harness):
    client, calls = harness
    client.get("/api/v1/briefing/madrid")
    client.get("/api/v1/briefing/madrid")
    assert calls["geo"] == 1
    assert calls["weather"] == 2  # forecast is live on every request


def test_circuit_opens_and_fails_fast(harness):
    client, calls = harness
    calls["weather_failures_left"] = 99
    # retry re-invokes the method directly, so the breaker sees ONE failure
    # per request; failure_threshold=3 opens the circuit after 3 requests
    for _ in range(3):
        assert client.get("/api/v1/briefing/madrid").status_code == 503
    weather_calls_after_retries = calls["weather"]
    # breaker is open: the next request must not reach the upstream at all
    assert client.get("/api/v1/briefing/madrid").status_code == 503
    assert calls["weather"] == weather_calls_after_retries
