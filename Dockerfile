# Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir requests beautifulsoup4 prometheus-client

# Copy the application
COPY scrape_modem.py /app/scrape_modem.py

# Set working directory
WORKDIR /app

# Run the application
CMD ["python", "scrape_modem.py"]