FROM debian:12-slim

ADD https://deb.globaleaks.org/install-globaleaks.sh install.sh

ARG VERSION
RUN bash install.sh -y -n -v "${VERSION}" && \
    apt-get install curl -y && \
    rm -rf install.* /var/lib/apt/lists/*

USER 1337

WORKDIR /var/globaleaks
VOLUME /var/globaleaks

HEALTHCHECK --interval=10s --timeout=3s \
  CMD curl -f -k https://localhost:8443/api/health || exit 1

EXPOSE 8443 8080

CMD ["globaleaks", "-n"]
