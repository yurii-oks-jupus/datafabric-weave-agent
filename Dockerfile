# ============================================================
# Weave Agent — Production Container
# ============================================================
FROM nexus3.systems.uk.hsbc:18080/com/hsbc/mss/cloud/python:3.13

WORKDIR /app
ENV PYTHONWARNINGS=ignore:InsecureRequestWarning

# Verify Python
RUN which python3 && python3 --version || \
    (apt-get update && apt-get install -y python3 python3-pip && ln -sf /usr/bin/python3 /usr/bin/python)

# Copy project
COPY . /app/
COPY hsbc-truststore.pem /etc/ssl/certs/hsbc-truststore.pem

# pip configuration
RUN echo "[global]" > /etc/pip.conf && \
    echo "timeout=180" >> /etc/pip.conf && \
    echo "index=https://vagrant:vagrant@gbmt-nexus.prd.fx.gbm.cloud.uk.hsbc/repository/pypi-group/pypi" >> /etc/pip.conf && \
    echo "index-url=https://vagrant:vagrant@gbmt-nexus.prd.fx.gbm.cloud.uk.hsbc/repository/pypi-group/simple" >> /etc/pip.conf && \
    echo "cert=/etc/ssl/certs/hsbc-truststore.pem" >> /etc/pip.conf

# Install dependencies
RUN pip install --no-cache-dir --break-system-packages \
    --trusted-host=nexus302.systems.uk.hsbc \
    -r requirements.txt

# Environment
ENV REQUESTS_CA_BUNDLE="/app/fabric_dev_crt.pem"
ENV SSL_CERT_FILE="/app/fabric_dev_crt.pem"
ENV APP_ENV="dev"
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

# Default: FastAPI mode. Override with CMD ["python3", "main.py", "--a2a"] for A2A.
ENTRYPOINT ["python3", "main.py"]
