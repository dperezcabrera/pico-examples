"""In-memory stand-in for the aio-pika surface pico-rabbitmq uses: the only
infrastructure boundary this example has. Routing is real topic matching."""

import fnmatch

import pico_rabbitmq.registrar as registrar_module
import pytest


class FakeMessage:
    def __init__(self, body: bytes):
        self.body = body
        self.acked = False
        self.rejected = False

    def process(self, requeue=False):
        message = self

        class _Ack:
            async def __aenter__(self):
                return message

            async def __aexit__(self, exc_type, exc, tb):
                if exc_type is None:
                    message.acked = True
                else:
                    message.rejected = True
                return False

        return _Ack()


class FakeQueue:
    def __init__(self, name):
        self.name = name
        self.callback = None
        self.bindings = []

    async def bind(self, exchange, routing_key=""):
        self.bindings.append((exchange.name, routing_key))

    async def consume(self, callback):
        self.callback = callback


class FakeExchange:
    def __init__(self, broker, name):
        self._broker = broker
        self.name = name

    async def publish(self, message, routing_key=""):
        for queue in self._broker.queues.values():
            bound = any(
                exchange == self.name and fnmatch.fnmatch(routing_key, pattern)
                for exchange, pattern in queue.bindings
            )
            if bound and queue.callback is not None:
                delivered = FakeMessage(message.body)
                self._broker.delivered.append(delivered)
                await queue.callback(delivered)


class FakeChannel:
    def __init__(self, broker):
        self._broker = broker
        self.default_exchange = FakeExchange(broker, "")

    async def set_qos(self, prefetch_count):
        pass

    async def declare_exchange(self, name, type_, durable=True):
        return FakeExchange(self._broker, name)

    async def declare_queue(self, name, durable=True):
        self._broker.queues[name] = FakeQueue(name)
        return self._broker.queues[name]


class FakeConnection:
    def __init__(self, broker):
        self._broker = broker

    async def channel(self):
        return FakeChannel(self._broker)

    async def close(self):
        pass


class FakeBroker:
    def __init__(self):
        self.queues = {}
        self.delivered = []

    async def connect_robust(self, url):
        return FakeConnection(self)

    @staticmethod
    def ExchangeType(value):
        return value

    class Message:
        def __init__(self, body, content_type=""):
            self.body = body
            self.content_type = content_type


@pytest.fixture
def broker(monkeypatch):
    fake = FakeBroker()
    monkeypatch.setattr(registrar_module, "aio_pika", fake)
    return fake
