"""Order intake backed by real infrastructure when deployed (Postgres,
Redis) and by sqlite plus fakeredis in the hermetic test suite. The
/actuator/health endpoint drives the container healthcheck and the
Kubernetes probes."""

import asyncio

from pydantic import BaseModel, Field
from sqlalchemy import String

from pico_caching import cacheable
from pico_fastapi import controller, get, post
from pico_ioc import component
from pico_sqlalchemy import (
    AppBase,
    Mapped,
    SessionManager,
    get_session,
    mapped_column,
    query,
    repository,
    transactional,
)


class Order(AppBase):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50))
    amount_cents: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))


class OrderRequest(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1)


@repository(entity=Order)
class OrderRepository:
    def __init__(self, session_manager: SessionManager):
        self.sm = session_manager

    async def save(self, sku: str, amount_cents: int) -> Order:
        session = get_session(self.sm)
        order = Order(sku=sku, amount_cents=amount_cents, status="placed")
        session.add(order)
        await session.flush()
        return order

    @query(expr="status = :status")
    async def find_by_status(self, status: str) -> list[Order]: ...


@component
class SchemaSetup:
    """Create tables on startup (use Alembic in production: database.migrations_path).
    pico-sqlalchemy >= 0.5.1 runs this hook off the event loop in every context."""

    def configure_database(self, engine) -> None:
        async def _create():
            async with engine.begin() as conn:
                await conn.run_sync(AppBase.metadata.create_all)
            # pooled connections bind to the DDL loop; drop them so
            # request-time loops get fresh ones
            await engine.dispose()

        asyncio.run(_create())


@component
class Catalog:
    """Prices live in Redis once looked up: every replica shares the cache."""

    def __init__(self):
        self.lookups = 0

    @cacheable(ttl_seconds=300)
    def price_cents(self, sku: str) -> int:
        self.lookups += 1
        return {"ESPRESSO": 250, "LATTE": 390}.get(sku, 999)


@component
class OrderService:
    def __init__(self, repo: OrderRepository, catalog: Catalog):
        self._repo = repo
        self._catalog = catalog

    @transactional
    async def place(self, request: OrderRequest) -> dict:
        amount = self._catalog.price_cents(request.sku) * request.quantity
        order = await self._repo.save(request.sku, amount)
        return {"id": order.id, "sku": order.sku, "amount_cents": amount, "status": order.status}


@controller(prefix="/api/v1/orders", tags=["Orders"])
class OrderController:
    def __init__(self, service: OrderService, repo: OrderRepository):
        self._service = service
        self._repo = repo

    @post("")
    async def place_order(self, request: OrderRequest):
        return await self._service.place(request)

    @get("")
    async def placed_orders(self):
        orders = await self._repo.find_by_status("placed")
        return [{"id": o.id, "sku": o.sku} for o in orders]
