"""Quotes priced by the service layer. Validation lives on the method, so a
CLI, a worker and an HTTP handler all get the same guarantees."""

from typing import ClassVar, Literal

from pico_ioc import component
from pico_pydantic import validate
from pydantic import BaseModel, Field


class QuoteRequest(BaseModel):
    sku: str = Field(min_length=3)
    quantity: int = Field(gt=0, le=1000)
    currency: Literal["EUR", "USD"] = "EUR"


class Quote(BaseModel):
    sku: str
    quantity: int
    currency: str
    total_cents: int


@component
class PriceBook:
    """Unit prices in EUR cents; USD applies a flat rate for the example."""

    prices: ClassVar[dict[str, int]] = {"LATTE": 390, "BAGEL": 250, "JUICE": 420}
    usd_rate = 1.1

    def unit_cents(self, sku: str, currency: str) -> int:
        if sku not in self.prices:
            raise LookupError(f"unknown sku {sku}")
        cents = self.prices[sku]
        return round(cents * self.usd_rate) if currency == "USD" else cents


@component
class QuoteService:
    def __init__(self, prices: PriceBook):
        self._prices = prices

    @validate
    def quote(self, request: QuoteRequest) -> Quote:
        unit = self._prices.unit_cents(request.sku, request.currency)
        return Quote(
            sku=request.sku,
            quantity=request.quantity,
            currency=request.currency,
            total_cents=unit * request.quantity,
        )

    @validate
    async def quote_many(self, requests: list[QuoteRequest]) -> list[Quote]:
        return [self.quote(request) for request in requests]
