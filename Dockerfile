FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# copy project
COPY . /app

# install deps (editable so code paths are clean)
RUN python -m pip install --upgrade pip && \
    python -m pip install -e .[dev]

# default command (overridden by compose)
CMD ["python", "-m", "apps.workers.featurizer_daemon"]