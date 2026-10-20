FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a non-root user; /data holds the SQLite DB and uploaded images (a volume).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /app/staticfiles \
    && chown -R app:app /data /app

COPY --chown=app:app . .
# Tolerate Windows (CRLF) line endings in the entrypoint script.
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
