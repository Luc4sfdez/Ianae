# === Stage 1: Builder ===
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY src/ ./src/
COPY pyproject.toml .

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV IANAE_ENV=production
ENV IANAE_DATA_DIR=/app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from src.core.nucleo import ConceptosLucas; print('ok')" || exit 1

CMD ["python", "-c", "from src.core.nucleo import ConceptosLucas; s = ConceptosLucas(); print(f'IANAE running — {s.dim_vector}d vectors')"]
