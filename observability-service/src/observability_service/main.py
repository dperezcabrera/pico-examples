"""Import-safe entry point: nothing starts at module level.

    uvicorn --factory observability_service.main:create_app
"""

import os

from fastapi import FastAPI
from pico_ioc import YamlTreeSource, configuration, init


def create_app() -> FastAPI:
    config_path = os.environ.get("CONFIG_PATH", "config/application.yaml")
    container = init(
        modules=["observability_service", "pico_fastapi", "pico_actuator", "pico_otel"],
        config=configuration(YamlTreeSource(config_path)),
    )
    return container.get(FastAPI)
