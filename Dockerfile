FROM python:3.13-alpine3.24
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apk upgrade --no-cache
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel
RUN addgroup -S app && adduser -S -G app app
COPY --chown=app:app . .
RUN chown app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && exec gunicorn valaproject.wsgi:application --bind 0.0.0.0:8000"]
