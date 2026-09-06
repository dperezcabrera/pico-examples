"""One publisher, three queues bound with different routing keys on the same
exchange: a created order reaches the projection, a cancellation reaches the
projection and the audit. State lives in an injected singleton."""

from pico_ioc import component
from pico_rabbitmq import consumer, publish, publisher


@publisher
class OrderEvents:
    @publish(exchange="events", routing_key="orders.created")
    def order_created(self, message): ...

    @publish(exchange="events", routing_key="orders.cancelled")
    def order_cancelled(self, message): ...


@component
class Inventory:
    def __init__(self):
        self.reserved: dict[str, int] = {}

    def adjust(self, sku: str, delta: int) -> None:
        self.reserved[sku] = self.reserved.get(sku, 0) + delta


@component
class StockProjection:
    def __init__(self, inventory: Inventory):
        self._inventory = inventory

    @consumer("stock-reservations", exchange="events", routing_key="orders.created")
    def reserve(self, message: dict):
        self._inventory.adjust(message["sku"], message["quantity"])

    @consumer("stock-releases", exchange="events", routing_key="orders.cancelled")
    def release(self, message: dict):
        self._inventory.adjust(message["sku"], -message["quantity"])


@component
class CancellationAudit:
    def __init__(self):
        self.entries: list[int] = []

    @consumer("cancellation-audit", exchange="events", routing_key="orders.cancelled")
    async def record(self, message: dict):
        self.entries.append(message["order_id"])
