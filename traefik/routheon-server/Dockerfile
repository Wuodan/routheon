FROM python:slim

# security / reproducibility basics
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies and create user
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy app code
COPY routheon-server.py /app/

USER appuser

EXPOSE 9080

# run the tiny stdlib HTTP server in that script
CMD ["python3", "routheon-server.py", \
     "--mappings", "/etc/traefik/mappings", \
     "--host", "0.0.0.0", \
     "--port", "9080", \
     "--skip-mapping", "routheon-server.yml"]
