"""In-memory stand-in for the aiokafka surface pico-kafka uses: the only
infrastructure boundary this example has. Every consumer of a topic gets
every record, exactly like independent consumer groups."""

import asyncio

import pico_kafka.registrar as registrar_module
import pytest


class FakeRecord:
    def __init__(self, value: bytes):
        self.value = value


class FakeConsumer:
    def __init__(self, bus, topic, group_id):
        self._bus = bus
        self.topic = topic
        self.group_id = group_id
        self.queue = None
        self.stopped = False

    async def start(self):
        self.queue = asyncio.Queue()
        self._bus.consumers.setdefault(self.topic, []).append(self)

    async def stop(self):
        self.stopped = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.stopped:
            raise StopAsyncIteration
        return await self.queue.get()


class FakeProducer:
    def __init__(self, bus):
        self._bus = bus

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_and_wait(self, topic, value):
        for consumer in self._bus.consumers.get(topic, []):
            await consumer.queue.put(FakeRecord(value))


class FakeBus:
    def __init__(self):
        self.consumers = {}

    def AIOKafkaConsumer(self, topic, *, bootstrap_servers, group_id):
        return FakeConsumer(self, topic, group_id)

    def AIOKafkaProducer(self, *, bootstrap_servers):
        return FakeProducer(self)


@pytest.fixture
def bus(monkeypatch):
    fake = FakeBus()
    monkeypatch.setattr(registrar_module, "aiokafka", fake)
    return fake
