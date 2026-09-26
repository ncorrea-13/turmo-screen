FROM docker.io/library/python:3.13-slim

ARG HEIMDALL_VERSION=v2.7.4
ARG HEIMDALL_ARCH=linux_arm64

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core curl ca-certificates \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-cli_${HEIMDALL_ARCH}" -o /usr/local/bin/heimdall-cli \
    && chmod +x /usr/local/bin/heimdall-cli \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY turmo/ turmo/
COPY turmo_lite.py .

ENTRYPOINT ["python", "turmo_lite.py"]
CMD ["--fleet", "--port", "/dev/ttyACM0"]
