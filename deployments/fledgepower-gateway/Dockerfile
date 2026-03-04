FROM python:3.11-slim

WORKDIR /app

# Install required Python packages
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    redis==5.0.1 \
    requests==2.31.0

# Create mock FledgePOWER HTTP server
COPY mock_fledge_server.py .

# OpenShift対応：ランダムユーザーIDでも読み取り可能にする
RUN chmod -R g+rwX /app

EXPOSE 8081 1995

CMD ["python3", "mock_fledge_server.py"]
