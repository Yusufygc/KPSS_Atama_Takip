# KPSS Atama Takip - Production Dockerfile
FROM python:3.12-slim

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    APP_DEBUG=false \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

WORKDIR /app

# Sistem paketleri (curl healthcheck, chromium İlan.gov.tr headless kazıma için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Root olmayan çalışma kullanıcısı
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --create-home app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY --chown=app:app app/ ./app/
COPY --chown=app:app web/ ./web/
COPY --chown=app:app run.py .
COPY --chown=app:app scripts/ ./scripts/

# Veri ve log dizinleri (volume bağlanan dizinler için sahiplik)
RUN mkdir -p data/documents logs && chown -R app:app data logs

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "run.py"]
