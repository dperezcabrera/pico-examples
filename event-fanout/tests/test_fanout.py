from event_fanout.app import CancellationAudit, Inventory, OrderEvents

CONFIG = {"rabbitmq": {"url": "amqp://fake/"}}


def test_created_events_reach_only_the_reservation_queue(make_container, broker):
    container = make_container("pico_rabbitmq", config=CONFIG)
    container.get(OrderEvents).order_created(
        {"order_id": 1, "sku": "LATTE", "quantity": 2}
    )
    assert container.get(Inventory).reserved == {"LATTE": 2}
    assert container.get(CancellationAudit).entries == []


def test_cancellation_fans_out_to_projection_and_audit(make_container, broker):
    container = make_container("pico_rabbitmq", config=CONFIG)
    events = container.get(OrderEvents)
    events.order_created({"order_id": 1, "sku": "LATTE", "quantity": 2})
    events.order_created({"order_id": 2, "sku": "LATTE", "quantity": 3})
    events.order_cancelled({"order_id": 2, "sku": "LATTE", "quantity": 3})
    assert container.get(Inventory).reserved == {"LATTE": 2}
    assert container.get(CancellationAudit).entries == [2]
    assert set(broker.queues) == {
        "stock-reservations",
        "stock-releases",
        "cancellation-audit",
    }


def test_poison_message_is_rejected_without_requeue_and_the_queue_moves_on(
    make_container, broker
):
    container = make_container("pico_rabbitmq", config=CONFIG)
    events = container.get(OrderEvents)
    events.order_created({"order_id": 3, "quantity": 1})  # no sku: the handler raises
    poison = broker.delivered[-1]
    assert poison.rejected is True
    assert poison.acked is False
    events.order_created({"order_id": 4, "sku": "BAGEL", "quantity": 1})
    assert container.get(Inventory).reserved == {"BAGEL": 1}
