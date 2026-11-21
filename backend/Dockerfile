FROM node:20-bookworm-slim AS frontend-build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY frontend ./frontend
COPY backend/ml_models ./backend/ml_models
RUN cd frontend && npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY --from=frontend-build /src/frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
