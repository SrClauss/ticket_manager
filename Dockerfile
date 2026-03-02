# Multi-stage Dockerfile: build Tailwind CSS + React Editor, then Python app

# ============================================
# Stage 1: Build Tailwind CSS
# ============================================
FROM node:20-alpine AS tailwind_builder
WORKDIR /build

# Copy tailwind config
COPY package.json package-lock.json* ./
COPY tailwind.config.js postcss.config.js ./
COPY app/static/css/tailwind_input.css ./app/static/css/

# Build Tailwind
RUN npm install --no-audit --no-fund
RUN npm run build:css

# ============================================
# Stage 2: Build React Editor
# ============================================
FROM node:20-alpine AS react_builder
WORKDIR /build

# Copy React app package files and install deps
COPY editor-de-layout-de/package.json editor-de-layout-de/package-lock.json* ./
RUN npm install --frozen-lockfile || npm install

COPY editor-de-layout-de/ ./
RUN npm run build

# ============================================
# Stage 3: Python Runtime (FastAPI)
# ============================================
FROM python:3.11-slim
WORKDIR /app

# System deps (Pillow, fonts)
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    fonts-dejavu-core \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY ./app /app/app

# Copy built Tailwind CSS
COPY --from=tailwind_builder /build/app/static/css/tailwind.css /app/app/static/css/tailwind.css

# Copy built React Editor
COPY --from=react_builder /build/dist /app/app/static/editor/

# Create directories
RUN mkdir -p /app/app/static/uploads /app/app/static/ingressos

EXPOSE 8000

# Health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/docs || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
