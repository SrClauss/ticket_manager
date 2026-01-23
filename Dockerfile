FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including image libraries for Pillow and fonts for ticket rendering)
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, templates, and static files
COPY ./app /app/app

# Create upload and ingressos directories
RUN mkdir -p /app/app/static/uploads /app/app/static/ingressos

# Expose the port
EXPOSE 8000

# Run the application with reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
