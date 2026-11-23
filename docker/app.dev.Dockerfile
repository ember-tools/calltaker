FROM python:3.14-slim

WORKDIR /app
ENV PIPENV_VENV_IN_PROJECT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATEN_VERZEICHNIS=/data
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && pipenv sync --dev

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]
