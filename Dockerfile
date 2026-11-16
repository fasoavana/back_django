# Build and runtime share the same Python/musl ABI. Only binary wheels are
# accepted; a missing wheel fails the build instead of adding compilers.
FROM python:3.13-alpine3.24@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e AS dependencies
WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN python -m venv --without-pip /opt/venv \
 && python -m pip --python /opt/venv install --no-cache-dir --only-binary=:all: -r requirements.txt

FROM python:3.13-alpine3.24@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH PYTHONPATH=/app CATALOG_DATA_DIR=/app/data
WORKDIR /app
RUN apk upgrade --no-cache \
 && python -m pip uninstall -y pip \
 && python -c "import shutil; shutil.rmtree('/usr/local/lib/python3.13/ensurepip')" \
 && addgroup -S -g 10001 newarrivals \
 && adduser -S -D -H -u 10001 -G newarrivals newarrivals
COPY --from=dependencies /opt/venv /opt/venv
COPY manage.py ./manage.py
COPY valaproject/ ./valaproject/
COPY shop/ ./shop/
COPY data/ ./data/
COPY deploy/wait_for_db.py ./deploy/wait_for_db.py
COPY deploy/start.sh ./deploy/start.sh
RUN mkdir -p /app/media /app/staticfiles /tmp/gunicorn \
 && chown -R 10001:10001 /app /tmp/gunicorn \
 && chmod +x /app/deploy/start.sh
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=80s --retries=3 \
 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=3)" || exit 1
CMD ["/bin/sh","/app/deploy/start.sh"]
