# Stage 1: Build Frontend (Node.js)
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY helio-yajna-frontend/package*.json ./
RUN npm ci

COPY helio-yajna-frontend/ ./
RUN npm run build

# Stage 2: Fullstack Python Backend & Static Server
FROM python:3.10-slim

WORKDIR /app

# System dependencies for OpenCV & image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install CPU PyTorch & dependencies
COPY environment_details/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn fastapi python-multipart aiofiles

# Copy project files
COPY . /app

# Copy built frontend assets into the app for all-in-one serving
COPY --from=frontend-builder /app/frontend/dist /app/helio-yajna-frontend/dist

ENV PYTHONUNBUFFERED=1
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics
ENV PORT=7860

EXPOSE 7860

# Launch all-in-one server (serves frontend UI on / and API on /api)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
