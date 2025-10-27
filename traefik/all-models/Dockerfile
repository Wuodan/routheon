FROM python:slim

# security / reproducibility basics
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies and create user
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

# Copy app code
COPY all-models.py /app/

USER appuser

EXPOSE 9080

# run the tiny stdlib HTTP server in that script
CMD ["python3", "all-models.py", \
     "--mappings", "/etc/traefik/mappings", \
     "--host", "0.0.0.0", \
     "--port", "9080", \
     "--skip-mapping", "all-models.yml"]
