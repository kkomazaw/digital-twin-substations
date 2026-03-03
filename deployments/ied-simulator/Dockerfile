FROM python:3.11-slim

WORKDIR /app

COPY ied_simulator.py .
COPY ied_http_server.py .

RUN chmod +x ied_simulator.py ied_http_server.py

# デフォルトはHTTPサーバーモード（FledgePOWER対応）
CMD ["python3", "ied_http_server.py"]
