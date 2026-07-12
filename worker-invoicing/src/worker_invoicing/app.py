"""Invoicing pipeline: pending orders are swept by an in-process scheduler
and turned into invoices by a DI-aware Celery task. In production the task
runs on a worker (celery -A ... worker); the wiring here is identical."""

import threading

from celery import Celery

from pico_celery import task
from pico_ioc import component
from pico_scheduling import scheduled


@component
class Ledger:
    """In-memory stand-in for the billing database."""

    def __init__(self):
        self.pending: list[int] = []
        self.invoices: list[dict] = []
        self.swept = threading.Event()
        self._lock = threading.Lock()

    def take_pending(self) -> list[int]:
        with self._lock:
            batch, self.pending = self.pending, []
            return batch

    def record(self, invoice: dict) -> None:
        with self._lock:
            self.invoices.append(invoice)


@component(scope="prototype")
class InvoiceTasks:
    """Celery tasks resolve their dependencies through the container per run."""

    def __init__(self, ledger: Ledger):
        self._ledger = ledger

    @task(name="invoices.generate")
    async def generate(self, order_id: int) -> dict:
        invoice = {"order_id": order_id, "pdf": f"invoice-{order_id}.pdf"}
        self._ledger.record(invoice)
        return invoice


@component
class InvoiceSweep:
    """Every sweep drains pending orders and enqueues one task per order."""

    def __init__(self, ledger: Ledger, celery: Celery):
        self._ledger = ledger
        self._celery = celery

    @scheduled(every=0.05)
    def sweep(self):
        for order_id in self._ledger.take_pending():
            self._celery.tasks["invoices.generate"].delay(order_id)
        self._ledger.swept.set()
