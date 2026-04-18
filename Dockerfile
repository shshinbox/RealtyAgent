FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지 (spacy, onnxruntime, sentencepiece 빌드에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# torch CPU 전용 먼저 설치 (CUDA 버전 받지 않도록 index-url 지정)
RUN pip install --no-cache-dir \
    torch==2.10.0 \
    --index-url https://download.pytorch.org/whl/cpu

# 나머지 의존성 설치
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# 소스 복사
COPY . .

# 로그 디렉토리
RUN mkdir -p logs

EXPOSE 8000
