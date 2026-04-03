FROM registry.access.redhat.com/ubi9/python-311:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY consumer.py .

CMD ["python3", "consumer.py"]
