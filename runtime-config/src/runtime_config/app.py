"""Operational hot reload: resilience policies react to config changes
applied through POST /actuator/refresh (the Spring Cloud refresh mirror),
with no process restart. A flaky dependency makes the effect observable:
with retry enabled the API absorbs the failures; disable resilience via
refresh and the same failure surfaces immediately."""

from fastapi import HTTPException

from pico_fastapi import controller, get
from pico_ioc import component
from pico_resilience import retryable


class QuoteUnavailable(Exception):
    pass


@component
class FlakyQuoteFeed:
    """Fails twice after every recovery: visible only without retry."""

    def __init__(self):
        self.calls = 0

    def spot_price(self) -> float:
        self.calls += 1
        if self.calls % 3 != 0:
            raise QuoteUnavailable("feed hiccup")
        return 101.25


@component
class QuoteService:
    def __init__(self, feed: FlakyQuoteFeed):
        self._feed = feed

    @retryable(max_attempts=3, backoff_seconds=0.01, retry_on=(QuoteUnavailable,))
    def quote(self) -> dict:
        return {"spot": self._feed.spot_price()}


@controller(prefix="/api/v1/quotes", tags=["Quotes"])
class QuoteController:
    def __init__(self, service: QuoteService):
        self._service = service

    @get("")
    async def quote(self):
        try:
            return self._service.quote()
        except QuoteUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
