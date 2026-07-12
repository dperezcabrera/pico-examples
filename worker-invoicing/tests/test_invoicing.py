import time

from celery import Celery

from worker_invoicing.app import Ledger

CONFIG = {
    "celery": {"broker_url": "memory://", "backend_url": "cache+memory://"},
    "scheduling": {"enabled": True},
}


def test_scheduler_sweeps_pending_orders_into_invoices(make_container):
    container = make_container("pico_celery", "pico_scheduling", config=CONFIG)
    # eager mode executes the enqueued task in-process; a real deployment
    # runs the same task on a celery worker
    container.get(Celery).conf.task_always_eager = True

    ledger = container.get(Ledger)
    ledger.pending.extend([101, 102])

    assert ledger.swept.wait(timeout=5), "scheduler never fired"
    deadline = time.time() + 5
    while len(ledger.invoices) < 2 and time.time() < deadline:
        time.sleep(0.02)

    assert sorted(i["order_id"] for i in ledger.invoices) == [101, 102]
    assert ledger.invoices[0]["pdf"] == "invoice-101.pdf"
    assert ledger.pending == []


def test_task_is_registered_for_external_workers(make_container):
    container = make_container("pico_celery", "pico_scheduling", config=CONFIG)
    assert "invoices.generate" in container.get(Celery).tasks
