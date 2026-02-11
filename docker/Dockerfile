FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar y instalar dependencias primero (mejor cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Crear directorio para datos persistentes
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "src.core.nucleo"]
