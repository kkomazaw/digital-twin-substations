FROM registry.access.redhat.com/ubi9/python-311:latest

USER 0

WORKDIR /opt/app-root/src

COPY ied_simulator.py .
COPY ied_http_server.py .

RUN chmod -R 775 /opt/app-root/src && \
    chown -R 1001:0 /opt/app-root/src

USER 1001

# プッシュモード：Edge Collectorにデータを送信
CMD ["python3", "ied_simulator.py"]
