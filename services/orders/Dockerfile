FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG APP_VERSION=development
ENV APP_VERSION=${APP_VERSION}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
EXPOSE 8001
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "app:app"]