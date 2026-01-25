# Multi-stage Dockerfile: build Tailwind CSS with Node, then build Python image

# --- Builder: build Tailwind CSS ---
FROM node:18-bullseye-slim AS node_builder
WORKDIR /build

# Install build deps (minimal)
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy only what is needed for tailwind build
COPY package.json package-lock.json* ./
COPY tailwind.config.js postcss.config.js ./
COPY app/static/css/tailwind_input.css ./app/static/css/

# Install node deps and build CSS
RUN npm install --no-audit --no-fund
RUN npm run build:css

# --- Final: Python app image ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (including image libraries for Pillow and fonts for ticket rendering)
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, templates, and static files
COPY ./app /app/app

# Copy built Tailwind CSS from builder
COPY --from=node_builder /build/app/static/css/tailwind.css /app/app/static/css/tailwind.css

# Create upload and ingressos directories
RUN mkdir -p /app/app/static/uploads /app/app/static/ingressos

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
