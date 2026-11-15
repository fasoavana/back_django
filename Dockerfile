# Dedicated root-build context for ValaDeploy (ProjectType.DOCKERFILE).
# DO NOT use COPY . . : ValaDeploy writes .env in the cloned context.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CATALOG_DATA_DIR=/app/data
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY manage.py ./manage.py
COPY valaproject/ ./valaproject/
COPY shop/ ./shop/
COPY data/ ./data/
COPY deploy/wait_for_db.py ./deploy/wait_for_db.py
COPY deploy/start.sh ./deploy/start.sh
RUN useradd --system --uid 10001 --home /app --shell /usr/sbin/nologin newarrivals \
  && mkdir -p /app/media /app/staticfiles /tmp/gunicorn \
  && chown -R 10001:10001 /app /tmp/gunicorn \
  && chmod +x /app/deploy/start.sh
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=80s --retries=3 \
 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=3)" || exit 1
CMD ["/bin/sh","/app/deploy/start.sh"]
