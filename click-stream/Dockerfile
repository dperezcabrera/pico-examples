FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -c https://raw.githubusercontent.com/dperezcabrera/pico-bom/main/2026.09.txt .

CMD ["python", "-m", "click_stream.smoke"]
