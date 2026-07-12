import pytest

from runtime_config.app import FlakyQuoteFeed

CONFIG = {
    "fastapi": {"title": "quotes"},
    "actuator": {},
    "resilience": {"enabled": True},
}


@pytest.fixture
def harness(make_container, make_client):
    # the dict IS the config source: mutating it and hitting /actuator/refresh
    # is the in-test equivalent of editing the config and asking a running
    # instance to re-read it
    config = {k: dict(v) for k, v in CONFIG.items()}
    container = make_container(
        "pico_fastapi", "pico_actuator", "pico_resilience", "pico_ioc.event_bus", config=config
    )
    return make_client(container), container, config


def test_retry_absorbs_the_flaky_feed(harness):
    client, container, _ = harness
    r = client.get("/api/v1/quotes")
    assert r.status_code == 200 and r.json() == {"spot": 101.25}
    assert container.get(FlakyQuoteFeed).calls == 3  # 2 hiccups swallowed


def test_refresh_disables_retry_without_restart(harness):
    client, container, config = harness
    assert client.get("/api/v1/quotes").status_code == 200

    config["resilience"]["enabled"] = False
    r = client.post("/actuator/refresh")
    assert r.status_code == 200 and r.json() == {"changed": ["resilience"]}

    feed = container.get(FlakyQuoteFeed)
    calls_before = feed.calls
    assert client.get("/api/v1/quotes").status_code == 503
    assert feed.calls == calls_before + 1  # single attempt, no retry

    config["resilience"]["enabled"] = True
    assert client.post("/actuator/refresh").json() == {"changed": ["resilience"]}
    assert client.get("/api/v1/quotes").status_code == 200
