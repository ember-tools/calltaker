FROM nixos/nix:latest AS frontend

WORKDIR /build
RUN nix-channel --update
COPY shell.nix .
COPY frontend/package*.json frontend/
RUN cd frontend && nix-shell ../shell.nix --run "npm ci"
COPY frontend/ frontend/
ARG COMMIT=dev
ARG BUILD_TIME
ENV COMMIT=$COMMIT BUILD_TIME=$BUILD_TIME
RUN mkdir src && cd frontend && nix-shell ../shell.nix --run "npm run build"


FROM python:3.14-slim

LABEL org.opencontainers.image.title="Calltaker" \
      org.opencontainers.image.description="Emergency call taking training for dispatch centres" \
      org.opencontainers.image.source="https://github.com/ember-tools/calltaker" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"
WORKDIR /app
RUN groupadd -r calltaker && useradd -r -g calltaker calltaker \
    && mkdir /data && chown calltaker:calltaker /data

ENV PIPENV_VENV_IN_PROJECT=1 \
    DATEN_VERZEICHNIS=/data
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && pipenv sync && pip uninstall -y pipenv

COPY src/ src/
COPY daten/ daten/
COPY --from=frontend /build/src/frontend_dist src/frontend_dist

USER calltaker
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/gesundheit')"]
CMD ["/app/.venv/bin/uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
