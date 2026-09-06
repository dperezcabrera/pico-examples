"""Against a real broker: publish, then watch the consumers converge.

RABBITMQ_URL=amqp://guest:guest@rabbitmq/ python -m event_fanout.smoke
"""

import os
import time

from pico_boot import init
from pico_ioc import DictSource, configuration

from event_fanout.app import CancellationAudit, Inventory, OrderEvents


def main() -> int:
    config = configuration(
        DictSource({"rabbitmq": {"url": os.environ["RABBITMQ_URL"]}})
    )
    container = init(modules=["event_fanout"], config=config)
    try:
        events = container.get(OrderEvents)
        events.order_created({"order_id": 1, "sku": "LATTE", "quantity": 2})
        events.order_created({"order_id": 2, "sku": "LATTE", "quantity": 3})
        events.order_cancelled({"order_id": 2, "sku": "LATTE", "quantity": 3})

        inventory, audit = container.get(Inventory), container.get(CancellationAudit)

        def converged() -> bool:
            return inventory.reserved.get("LATTE") == 2 and audit.entries == [2]

        deadline = time.monotonic() + 15
        while not converged() and time.monotonic() < deadline:
            time.sleep(0.1)
        print(f"reserved={inventory.reserved} cancellations={audit.entries}")
        if not converged():
            print("SMOKE FAILED: consumers never converged")
            return 1
        print("SMOKE OK: created and cancelled events routed through a real RabbitMQ")
        return 0
    finally:
        container.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
