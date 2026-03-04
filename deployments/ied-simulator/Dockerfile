FROM python:3.11-slim

WORKDIR /app

COPY ied_simulator.py .
COPY ied_http_server.py .

# OpenShift対応：ランダムユーザーIDでも読み取り可能にする
RUN chmod -R g+rwX /app

# プッシュモード：Edge Collectorにデータを送信
CMD ["python3", "ied_simulator.py"]
