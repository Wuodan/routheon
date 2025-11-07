FROM python:slim

# security / reproducibility basics
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install application and create user
ARG ROUTHEON_VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${ROUTHEON_VERSION}
COPY pyproject.toml README.md /tmp/routheon-server/
COPY routheon_server /tmp/routheon-server/routheon_server
RUN pip install --no-cache-dir /tmp/routheon-server && \
    rm -rf /tmp/routheon-server && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

WORKDIR /app
USER appuser

EXPOSE 9080

# run the tiny stdlib HTTP server
CMD ["routheon-server", \
     "--mappings", "/etc/traefik/mappings", \
     "--host", "0.0.0.0", \
     "--port", "9080", \
     "--skip-mapping", "routheon-server.yml", \
     "--stats-config-file", "/home/appuser/.routheon/stats-config.yml"]
