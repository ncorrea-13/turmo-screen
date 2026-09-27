FROM docker.io/library/python:3.14-alpine

ARG TARGETARCH
ARG HEIMDALL_VERSION=v2.7.4

RUN apk add --no-cache font-dejavu ca-certificates \
    && apk add --no-cache --virtual .fetch curl \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-cli_linux_${TARGETARCH}" -o /usr/local/bin/heimdall-cli \
    && chmod +x /usr/local/bin/heimdall-cli \
    && apk del .fetch

WORKDIR /app
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY turmo/ turmo/
COPY turmo_lite.py .

ENTRYPOINT ["python", "turmo_lite.py"]
CMD ["--fleet", "--port", "/dev/ttyACM0", "--width", "480", "--height", "320", "--orientation", "landscape", "--interval", "1", "--clear"]
