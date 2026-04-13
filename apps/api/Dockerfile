FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1             PYTHONUNBUFFERED=1             PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/api/requirements-dev.txt /app/apps/api/requirements-dev.txt

RUN python -m pip install --upgrade pip             && pip install -r /app/apps/api/requirements-dev.txt

COPY definitions /app/definitions
COPY scripts /app/scripts
COPY apps/api /app/apps/api

WORKDIR /app/apps/api
ENV PYTHONPATH=/app/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
