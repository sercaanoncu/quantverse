FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
COPY configs ./configs
COPY config ./config
COPY tests ./tests

RUN python -m pip install --upgrade pip && \
    python -m pip install -e .[dev]

CMD ["python", "scripts/run_full_pipeline.py", "--config", "configs/base.yaml"]
