FROM python:3.12-slim

# Print logs immediately; don't write .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Use uv for fast installs (same tool as on your Mac)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 1. Install libraries first (this layer is cached until requirements.txt changes)
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 2. Then copy our code (changes often, so it goes last)
COPY app/ app/
COPY ui/ ui/
COPY scripts/ scripts/
COPY eval/ eval/

# 3. Run as a normal user, not root (a security best practice)
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/sample_docs /app/chroma_db \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 8501

# Default command: start the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
