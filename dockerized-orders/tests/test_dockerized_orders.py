import fakeredis
import pytest


@pytest.fixture
def client(make_container, make_client, tmp_path, monkeypatch):
    # hermetic stand-ins for the compose services: sqlite for Postgres,
    # fakeredis for Redis; the app code is identical
    import pico_data_redis.factory as redis_factory

    server = fakeredis.FakeServer()
    monkeypatch.setattr(
        redis_factory.Redis,
        "from_url",
        classmethod(lambda cls, url, **kw: fakeredis.FakeRedis(server=server)),
    )
    container = make_container(
        "pico_fastapi",
        "pico_sqlalchemy",
        "pico_caching",
        "pico_data_redis",
        "pico_actuator",
        config={
            "fastapi": {"title": "orders"},
            "database": {"url": f"sqlite+aiosqlite:///{tmp_path}/orders.db"},
            "caching": {"enabled": True},
            "redis": {"url": "redis://stub:6379/0"},
            "actuator": {"info": {"app": "dockerized-orders"}},
        },
    )
    return make_client(container), container


def test_place_order_and_health(client):
    http, _ = client
    assert http.get("/actuator/health").json()["status"] == "UP"
    r = http.post("/api/v1/orders", json={"sku": "LATTE", "quantity": 2})
    assert r.status_code == 200 and r.json()["amount_cents"] == 780
    assert http.get("/api/v1/orders").json() == [{"id": r.json()["id"], "sku": "LATTE"}]


def test_catalog_cache_is_shared_through_redis(client):
    http, container = client
    from dockerized_orders.app import Catalog

    catalog = container.get(Catalog)
    http.post("/api/v1/orders", json={"sku": "LATTE"})
    http.post("/api/v1/orders", json={"sku": "LATTE"})
    assert catalog.lookups == 1  # second price came from the redis-backed cache


def test_factory_entrypoint_is_import_safe(tmp_path, monkeypatch):
    # importing main must not boot anything; create_app builds the app on demand
    import dockerized_orders.main as main

    (tmp_path / "test.yaml").write_text(
        f"""
fastapi:
  title: factory-check
database:
  url: sqlite+aiosqlite:///{tmp_path}/factory.db
caching:
  enabled: false
actuator: {{}}
"""
    )
    monkeypatch.setenv("PICO_BOOT_AUTO_PLUGINS", "false")
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path / "test.yaml"))
    app = main.create_app()
    assert app.title == "factory-check"
