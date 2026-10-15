FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SQLITE_PATH=/tmp/invoices.db
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 app
COPY app ./app
USER 10001
EXPOSE 8080
CMD ["python", "-m", "app.server"]
