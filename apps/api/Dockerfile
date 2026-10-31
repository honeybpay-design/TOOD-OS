FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/tood
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . \
    && mkdir -p /app/data/uploads /home/tood \
    && chown -R 10001:10001 /app/data /home/tood
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
