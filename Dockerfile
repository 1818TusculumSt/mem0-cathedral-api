FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app last (changes most frequently)
COPY main.py .

# Run with multiple workers for better throughput
# Uvicorn will use lifespan context manager for connection pooling
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
