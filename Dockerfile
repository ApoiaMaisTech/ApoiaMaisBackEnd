FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# dependências do Python (todas têm wheel para 3.11, sem compilador na imagem)
COPY requirements.txt .
RUN pip install -r requirements.txt

# código da aplicação (o .dockerignore deixa de fora .env, testes, docs e .git)
COPY . .

# roda sem root; /data/media é o volume de imagens (mesmo UID do go-worker)
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app \
    && mkdir -p /data/media && chown -R 10001:10001 /data
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=4).status == 200 else 1)"

# sem --reload: imagem de execução, não de desenvolvimento
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
