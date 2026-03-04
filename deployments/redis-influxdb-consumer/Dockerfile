FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer.py .

# OpenShift対応：ランダムユーザーIDでも読み取り可能にする
RUN chmod -R g+rwX /app

CMD ["python3", "consumer.py"]
