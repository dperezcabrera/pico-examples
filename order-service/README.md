# order-service

REST CRUD over pico-sqlalchemy with transactional integrity.

What to look at:

- `OrderRepository`: a `@repository` with an imperative `save` and a derived `@query(expr="status = :status")`.
- `OrderService.place` is `@transactional` and inserts BEFORE reserving stock on purpose: when `Stock.reserve` raises, the insert is rolled back. The test proves it by asserting the 409 response AND the empty listing afterwards.
- `SchemaSetup(DatabaseConfigurer)`: DDL on startup; production would point `database.migrations_path` at Alembic instead.

```bash
pip install -e ".[dev]" && pytest
```
