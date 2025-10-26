FROM python:slim

# security / reproducibility basics
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies and create user
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

# Copy app code
COPY all-models.py /app/

USER appuser

# run the tiny stdlib HTTP server in that script
CMD ["python3", "all-models.py", \
     "--mappings", "/etc/traefik/mappings", \
     "--host", "0.0.0.0", \
     "--port", "9080", \
     "--skip-mapping", "all-models.yml"]
