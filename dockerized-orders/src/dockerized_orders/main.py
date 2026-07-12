"""Import-safe entry point: nothing starts at module level.

    uvicorn --factory dockerized_orders.main:create_app
"""

import os

from fastapi import FastAPI
from pico_ioc import YamlTreeSource, configuration, init


def create_app() -> FastAPI:
    config_path = os.environ.get("CONFIG_PATH", "config/application.yaml")
    container = init(
        modules=[
            "dockerized_orders",
            "pico_fastapi",
            "pico_sqlalchemy",
            "pico_caching",
            "pico_data_redis",
            "pico_actuator",
        ],
        config=configuration(YamlTreeSource(config_path)),
    )
    return container.get(FastAPI)
