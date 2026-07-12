"""Order service: REST CRUD over SQLAlchemy with transactional integrity."""

import asyncio

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import String

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

PRICES = {"ESPRESSO": 250, "LATTE": 390}


class Order(AppBase):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column()
    amount_cents: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))


class OrderRequest(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1)


class OutOfStock(Exception):
    pass


@repository(entity=Order)
class OrderRepository:
    def __init__(self, session_manager: SessionManager):
        self.sm = session_manager

    async def save(self, sku: str, quantity: int, amount_cents: int) -> Order:
        session = get_session(self.sm)
        order = Order(sku=sku, quantity=quantity, amount_cents=amount_cents, status="placed")
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
            await engine.dispose()

        asyncio.run(_create())


@component
class Stock:
    def __init__(self):
        self.levels = {"ESPRESSO": 10, "LATTE": 10}

    def reserve(self, sku: str, quantity: int) -> None:
        available = self.levels.get(sku, 0)
        if quantity > available:
            raise OutOfStock(f"{sku}: requested {quantity}, available {available}")
        self.levels[sku] = available - quantity


@component
class OrderService:
    def __init__(self, repo: OrderRepository, stock: Stock):
        self._repo = repo
        self._stock = stock

    @transactional
    async def place(self, request: OrderRequest) -> dict:
        amount = PRICES.get(request.sku, 999) * request.quantity
        order = await self._repo.save(request.sku, request.quantity, amount)
        # reserve AFTER the insert on purpose: when stock rejects, the raise
        # crosses the @transactional boundary and rolls the row back
        self._stock.reserve(request.sku, request.quantity)
        return {"id": order.id, "sku": order.sku, "amount_cents": amount, "status": order.status}


@controller(prefix="/api/v1/orders", tags=["Orders"])
class OrderController:
    def __init__(self, service: OrderService, repo: OrderRepository):
        self._service = service
        self._repo = repo

    @post("")
    async def place_order(self, request: OrderRequest):
        try:
            return await self._service.place(request)
        except OutOfStock as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

    @get("")
    async def placed_orders(self):
        orders = await self._repo.find_by_status("placed")
        return [{"id": o.id, "sku": o.sku, "quantity": o.quantity} for o in orders]
