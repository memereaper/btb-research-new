FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-platform.lock ./
RUN pip install --no-cache-dir -r requirements-platform.lock
COPY btb_platform ./btb_platform
RUN useradd --uid 10001 --create-home app
USER 10001
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health/ready',timeout=3)"
CMD ["python","-m","btb_platform","serve","--host","0.0.0.0","--port","8787"]
