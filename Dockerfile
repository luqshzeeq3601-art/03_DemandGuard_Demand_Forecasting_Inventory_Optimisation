FROM python:3.11-slim

WORKDIR /app

# Install CBC solver and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    coinor-cbc \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification and code
COPY pyproject.toml README.md /app/
COPY src/ /app/src/
COPY config/ /app/config/
COPY artifacts/ /app/artifacts/

# Install python dependencies and editable package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "demandguard.api:app", "--host", "0.0.0.0", "--port", "8000"]
