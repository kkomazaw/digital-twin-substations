FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY edge_collector.py .

EXPOSE 8888

CMD ["python3", "edge_collector.py"]
