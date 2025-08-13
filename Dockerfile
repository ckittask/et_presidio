FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=presidio_flask_estbert.py
ENV FLASK_ENV=production
ENV PORT=8000
ENV HOST=0.0.0.0

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with fixed versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy models as root user (system-wide installation)
RUN python -m spacy download xx_ent_wiki_sm

# Create non-root user for security AFTER installing models
RUN groupadd -r presidio && useradd -r -g presidio -m presidio

# Create necessary directories and set proper ownership
RUN mkdir -p /app/config /app/logs /app/models && \
    chown -R presidio:presidio /app

# Copy application files
COPY --chown=presidio:presidio . .

# Create a simple health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:$PORT/ || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown presidio:presidio /app/healthcheck.sh

# Switch to non-root user
USER presidio

# Expose the port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD ./healthcheck.sh

# Default command
CMD ["python", "app.py"]