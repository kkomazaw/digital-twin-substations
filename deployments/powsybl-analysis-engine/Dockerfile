# マルチステージビルドで軽量化
FROM python:3.11-slim as builder

# ビルド用依存関係
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係のみ先にインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 最終イメージ
FROM python:3.11-slim

LABEL maintainer="Digital Twin Substations"
LABEL description="PowSyBl Advanced Analysis Engine"

# 実行時依存関係のみ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ビルダーからPythonパッケージをコピー
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# アプリケーションコードのコピー
COPY app/ ./app/

# ポート公開
EXPOSE 8001

# アプリケーション起動
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
