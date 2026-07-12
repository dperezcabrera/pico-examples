"""City briefing aggregator: two upstreams behind declarative HTTP clients,
hardened with retry, circuit breaker and a cached geocoder."""

import httpx
from fastapi import HTTPException

from pico_caching import cacheable
from pico_fastapi import controller, get
from pico_httpx import get as http_get
from pico_httpx import http_client
from pico_ioc import component
from pico_resilience import CircuitOpenError, RetryExhaustedError, circuit_breaker, retryable


@http_client(name="geo")
class GeoApi:
    @http_get("/geocode/{city}")
    async def locate(self, city: str) -> dict: ...


@http_client(name="weather")
class WeatherApi:
    @http_get("/forecast")
    async def forecast(self, lat: float, lon: float) -> dict: ...


@component
class Geocoder:
    """Coordinates never change: cache them so repeated briefings hit geo once."""

    def __init__(self, geo: GeoApi):
        self._geo = geo

    @cacheable(ttl_seconds=3600)
    async def locate(self, city: str) -> dict:
        return await self._geo.locate(city)


@component
class BriefingService:
    def __init__(self, geocoder: Geocoder, weather: WeatherApi):
        self._geocoder = geocoder
        self._weather = weather

    @retryable(max_attempts=3, backoff_seconds=0.01, retry_on=(httpx.HTTPError,))
    @circuit_breaker(failure_threshold=3, reset_timeout_seconds=60)
    async def briefing(self, city: str) -> dict:
        location = await self._geocoder.locate(city)
        forecast = await self._weather.forecast(lat=location["lat"], lon=location["lon"])
        return {"city": city, "coords": [location["lat"], location["lon"]], "forecast": forecast["summary"]}


@controller(prefix="/api/v1/briefing", tags=["Briefing"])
class BriefingController:
    def __init__(self, service: BriefingService):
        self._service = service

    @get("/{city}")
    async def briefing(self, city: str):
        try:
            return await self._service.briefing(city)
        except (RetryExhaustedError, CircuitOpenError, httpx.HTTPError) as e:
            raise HTTPException(status_code=503, detail=f"upstream unavailable: {e}") from e
