"""One topic, two consumer groups: each group receives every record, and a
record one handler cannot process is skipped instead of stalling the partition."""

from pico_ioc import component
from pico_kafka import kafka_consumer, kafka_producer, produce


@kafka_producer
class ClickEvents:
    @produce("clicks")
    def clicked(self, message): ...


@component
class PageViews:
    def __init__(self):
        self.by_page: dict[str, int] = {}

    @kafka_consumer("clicks")
    def count(self, message: dict):
        self.by_page[message["page"]] = self.by_page.get(message["page"], 0) + 1


@component
class SessionAudit:
    def __init__(self):
        self.sessions: list[str] = []

    @kafka_consumer("clicks", group_id="audit")
    async def record(self, message: dict):
        self.sessions.append(message["session"])
