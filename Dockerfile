# Dockerfile for Power Nowcast API
# Implements Section 13 containerization option

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Environment variables
ENV PYTHONPATH=/app
ENV MLFLOW_TRACKING_URI=http://localhost:5001
ENV MODEL_NAME=power-nowcast
ENV MODEL_STAGE=Production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command - can be overridden
CMD ["uvicorn", "src.serve.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
