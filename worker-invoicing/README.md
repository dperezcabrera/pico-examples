# worker-invoicing

Background work without a web layer: an in-process pico-scheduling sweep drains pending orders and enqueues a DI-aware pico-celery task per order.

What to look at:

- `InvoiceTasks` is `@component(scope="prototype")`: each task run resolves its dependencies through the container, exactly as on a real worker.
- `InvoiceSweep.sweep` runs every 50ms via `@scheduled(every=0.05)` and enqueues through the Celery app (`celery.tasks[...].delay`).
- The test flips `task_always_eager` to execute enqueued tasks in-process; deploying means running `celery worker` against a real broker with zero code changes.

```bash
pip install -e ".[dev]" && pytest
```
