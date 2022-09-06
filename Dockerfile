FROM alpine:3.16
LABEL maintainer="Thomas GUIRRIEC <thomas@guirriec.fr>"
ENV BINANCE_EXPORTER_PORT=8123
ENV BINANCE_EXPORTER_LOGLEVEL='INFO'
ENV BINANCE_EXPORTER_NAME='binance-exporter'
COPY requirements.txt /
COPY entrypoint.sh /
ENV VIRTUAL_ENV="/binance-exporter"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN apk add --no-cache --update \
         python3 \
    && python3 -m venv ${VIRTUAL_ENV} \
    && pip install --no-cache-dir --no-dependencies --no-binary :all: -r requirements.txt \
    && pip uninstall -y setuptools pip \
    && rm -rf \
        /root/.cache \
        /tmp/* \
        /var/cache/* \
    && chmod +x /entrypoint.sh
COPY binance_exporter.py ${VIRTUAL_ENV}
WORKDIR ${VIRTUAL_ENV}
HEALTHCHECK CMD nc -vz localhost ${BINANCE_EXPORTER_PORT} || exit 1
ENTRYPOINT ["/entrypoint.sh"]
