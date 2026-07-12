"""Job intake service that is fully observable: /actuator/* endpoints,
a real health indicator wired to business state, build info, a business
metric on prometheus' default registry (the pico-otel/actuator contract)
and OpenTelemetry traces on every request."""

from fastapi import HTTPException
from prometheus_client import Counter
from pydantic import BaseModel

from pico_fastapi import controller, get, post
from pico_ioc import component

JOBS_ACCEPTED = Counter("jobs_accepted_total", "Jobs accepted into the intake queue")


class JobRequest(BaseModel):
    payload: str


@component
class IntakeQueue:
    max_depth = 3

    def __init__(self):
        self.jobs: list[str] = []

    def push(self, payload: str) -> int:
        if len(self.jobs) >= self.max_depth:
            raise HTTPException(status_code=429, detail="queue full")
        self.jobs.append(payload)
        JOBS_ACCEPTED.inc()
        return len(self.jobs)


@component
class QueueHealth:
    """DOWN when the intake queue saturates: load balancers stop routing
    to this instance before it starts rejecting work."""

    name = "intake-queue"

    def __init__(self, queue: IntakeQueue):
        self._queue = queue

    def check(self):
        depth = len(self._queue.jobs)
        if depth >= self._queue.max_depth:
            raise RuntimeError(f"queue saturated: {depth}/{self._queue.max_depth}")
        return {"status": "UP", "depth": depth}


@component
class BuildInfo:
    def contribute(self):
        return {"build": {"version": "0.1.0", "commit": "example"}}


@controller(prefix="/api/v1/jobs", tags=["Jobs"])
class JobsController:
    def __init__(self, queue: IntakeQueue):
        self._queue = queue

    @post("")
    async def submit(self, request: JobRequest):
        return {"depth": self._queue.push(request.payload)}

    @get("")
    async def pending(self):
        return {"jobs": self._queue.jobs}
