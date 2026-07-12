# order-service

REST CRUD over pico-sqlalchemy with transactional integrity.

What to look at:

- `OrderRepository`: a `@repository` with an imperative `save` and a derived `@query(expr="status = :status")`.
- `OrderService.place` is `@transactional` and inserts BEFORE reserving stock on purpose: when `Stock.reserve` raises, the insert is rolled back. The test proves it by asserting the 409 response AND the empty listing afterwards.
- `SchemaSetup`: DDL on startup with plain `asyncio.run()` — pico-sqlalchemy >= 0.5.1 runs configurer hooks off the event loop in every boot context, and any `@component` with `configure_database()` is collected. Production would point `database.migrations_path` at Alembic instead.

```bash
pip install -e ".[dev]" && pytest
```
