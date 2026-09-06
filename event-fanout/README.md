# event-fanout

Topic routing over RabbitMQ: one publisher, three queues bound to the same exchange with different routing keys, consumers that share state through an injected singleton.

What to look at:

- `OrderEvents` is a `@publisher` with two stubs; each `@publish` names the exchange and routing key, the body is JSON-encoded for you.
- `StockProjection` consumes `orders.created` and `orders.cancelled` from two queues; `CancellationAudit` binds only `orders.cancelled`. A cancellation therefore reaches two consumers, a creation one.
- A message the handler cannot process (no `sku`) is rejected without requeue and the queue keeps flowing: asserted by the test through the message's ack/reject flags.
- Tests replace aio-pika with an in-memory broker that does real topic matching; `smoke.sh` runs the same code against a real RabbitMQ in Docker Compose, booted by `pico_boot.init`.

```bash
pip install -e ".[dev]" && pytest
./smoke.sh
```
