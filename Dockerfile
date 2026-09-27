FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 (garminconnect, fitparse 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (소스는 마운트)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 18080

ENV PYTHONPATH=/app

# 워커는 1개 유지(auto_sync 데몬·동기화/재계산 진행 상태가 프로세스 메모리에 있어 다중 워커면 중복 실행·상태 분열),
# 대신 gthread 스레드로 요청을 병렬 처리한다(단일 sync 워커에서 화면 API가 직렬로 줄 서던 문제).
CMD ["gunicorn", "--bind", "0.0.0.0:18080", "--worker-class", "gthread", "--workers", "1", "--threads", "8", "--reload", "--access-logfile", "-", "--error-logfile", "-", "src.serve:app"]
