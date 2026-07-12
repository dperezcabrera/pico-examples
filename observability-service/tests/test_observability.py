import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

CONFIG = {
    "fastapi": {"title": "jobs"},
    "actuator": {"info": {"app": "jobs"}},
    "otel": {"traces_exporter": "none", "service_name": "jobs"},
}


@pytest.fixture
def client(make_container, make_client):
    container = make_container("pico_fastapi", "pico_actuator", "pico_otel", config=CONFIG)
    return make_client(container)


def test_health_follows_business_state(client):
    assert client.get("/actuator/health").json()["status"] == "UP"

    for i in range(3):  # saturate the queue
        assert client.post("/api/v1/jobs", json={"payload": f"job-{i}"}).status_code == 200
    assert client.post("/api/v1/jobs", json={"payload": "overflow"}).status_code == 429

    health = client.get("/actuator/health")
    assert health.json()["status"] == "DOWN"
    assert health.status_code == 503


def test_info_exposes_build_contribution(client):
    info = client.get("/actuator/info").json()
    assert info["build"]["version"] == "0.1.0"
    assert info["app"] == "jobs"


def test_business_metric_reaches_actuator_metrics(client):
    before = _accepted_total(client)
    client.post("/api/v1/jobs", json={"payload": "metered"})
    assert _accepted_total(client) == before + 1


def test_requests_produce_spans(client):
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    client.get("/api/v1/jobs")
    names = [s.name for s in exporter.get_finished_spans()]
    assert any("/api/v1/jobs" in n for n in names), names


def _accepted_total(client) -> float:
    for line in client.get("/actuator/metrics").text.splitlines():
        if line.startswith("jobs_accepted_total"):
            return float(line.split()[-1])
    return 0.0
