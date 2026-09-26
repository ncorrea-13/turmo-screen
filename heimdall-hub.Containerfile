FROM docker.io/library/debian:trixie-slim

ARG TARGETARCH
ARG HEIMDALL_VERSION=v2.7.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-hub_linux_${TARGETARCH}" -o /usr/local/bin/heimdall-hub \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-daemon_linux_${TARGETARCH}" -o /usr/local/bin/heimdall-daemon \
    && chmod +x /usr/local/bin/heimdall-hub /usr/local/bin/heimdall-daemon \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 9090
ENTRYPOINT ["heimdall-hub"]
CMD ["--listen", ":9090"]
