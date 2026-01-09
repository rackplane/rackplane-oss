FROM python:3.11-slim

WORKDIR /app

# Create credentials directory
RUN mkdir -p /app/credentials

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    poppler-utils \
    tesseract-ocr \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (OSS version - no premium deps)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install optional dependencies (if exists)
COPY requirements-optional.txt* ./
RUN if [ -f requirements-optional.txt ]; then pip install --no-cache-dir -r requirements-optional.txt; fi

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
