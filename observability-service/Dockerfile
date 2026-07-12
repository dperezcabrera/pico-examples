FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . "pico-ioc[yaml]>=2.3.3" "uvicorn>=0.30"

COPY config ./config

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/actuator/health', timeout=2)"

CMD ["uvicorn", "--factory", "observability_service.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
