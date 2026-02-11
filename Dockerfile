# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install uv for lightning-fast dependency resolution
# We use the official binary installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies using uv
RUN uv pip install --no-cache --system -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads output_product_set

# Expose the API port
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
