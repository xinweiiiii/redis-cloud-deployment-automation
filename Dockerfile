# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY input/ /app/input/
COPY rest-api/ /app/rest-api/

# Create directory for temporary files
RUN mkdir -p /tmp/uploads && chmod 777 /tmp/uploads

# Make entrypoint script executable
RUN chmod +x /app/rest-api/entrypoint.sh

# Expose port 9000 (can be overridden with PORT env var)
EXPOSE 9000

# Set working directory to rest-api
WORKDIR /app/rest-api

# Set default PORT environment variable
ENV PORT=9000

# Health check - uses PORT env var
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"9000\")}/health')" || exit 1

# Run the application with entrypoint script
ENTRYPOINT ["/app/rest-api/entrypoint.sh"]
