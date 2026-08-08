FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/lesson12

RUN pip install --no-cache-dir \
      clickhouse-connect==0.8.18 \
      fastapi==0.116.1 \
      prometheus-client==0.22.1 \
      uvicorn==0.35.0 \
    && addgroup --system lesson12 \
    && adduser --system --ingroup lesson12 lesson12

COPY --chown=lesson12:lesson12 app/ ./app/

USER lesson12

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
