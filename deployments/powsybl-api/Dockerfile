# シンプルな単一ステージビルド
FROM python:3.11-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY api.py .

# OpenShift対応：ランダムユーザーIDでも読み取り可能にする
RUN chmod -R g+rwX /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
