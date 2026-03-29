FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 (garminconnect, fitparse 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (소스는 마운트)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 18080

ENV PYTHONPATH=/app
ENV FLASK_HOST=0.0.0.0
ENV FLASK_DEBUG=0

CMD ["python", "src/serve.py"]
