FROM docker.io/library/alpine:3.22

ARG TARGETARCH
ARG HEIMDALL_VERSION=v2.7.4

RUN apk add --no-cache ca-certificates \
    && apk add --no-cache --virtual .fetch curl \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-hub_linux_${TARGETARCH}" -o /usr/local/bin/heimdall-hub \
    && curl -fsSL "https://github.com/kinncj/Heimdall/releases/download/${HEIMDALL_VERSION}/heimdall-daemon_linux_${TARGETARCH}" -o /usr/local/bin/heimdall-daemon \
    && chmod +x /usr/local/bin/heimdall-hub /usr/local/bin/heimdall-daemon \
    && apk del .fetch

EXPOSE 9090
ENTRYPOINT ["heimdall-hub"]
CMD ["--listen", ":9090"]
