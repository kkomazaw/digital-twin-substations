#!/usr/bin/env python3
"""
Kafka to InfluxDB Consumer
Kafkaから変電所テレメトリデータを受信しInfluxDBに書き込む
"""
import json
import os
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 環境変数
KAFKA_BROKERS = os.environ.get('KAFKA_BROKERS', 'kafka.data-zone.svc.cluster.local:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'substation-telemetry')
KAFKA_GROUP_ID = os.environ.get('KAFKA_GROUP_ID', 'influxdb-consumer-group')

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb.data-zone.svc.cluster.local:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'substation')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'telemetry')

class KafkaInfluxDBConsumer:
    def __init__(self):
        self.consumer = None
        self.influx_client = None
        self.write_api = None

    def connect_kafka(self):
        """Kafka接続"""
        print(f"Connecting to Kafka: {KAFKA_BROKERS}")
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKERS.split(','),
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        print(f"✓ Subscribed to topic: {KAFKA_TOPIC}")

    def connect_influxdb(self):
        """InfluxDB接続"""
        print(f"Connecting to InfluxDB: {INFLUXDB_URL}")
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        print(f"✓ Connected to InfluxDB bucket: {INFLUXDB_BUCKET}")

    def process_message(self, message):
        """メッセージをInfluxDBポイントに変換"""
        data = message.value

        # タイムスタンプ
        timestamp = data.get('timestamp', datetime.utcnow().isoformat() + 'Z')

        # InfluxDBポイント作成
        point = Point("substation_telemetry") \
            .tag("station_id", data.get('station_id', 'unknown')) \
            .tag("ied_id", data.get('ied_id', 'unknown')) \
            .tag("type", data.get('type', 'SV'))

        # 計測値
        measurements = data.get('measurements', {})
        for key, value in measurements.items():
            if isinstance(value, (int, float)):
                point = point.field(key, float(value))

        # ステータス
        status = data.get('status', {})
        point = point.field("healthy", int(status.get('healthy', False)))
        point = point.field("alarm", int(status.get('alarm', False)))
        point = point.field("anomaly_detected", int(status.get('anomaly_detected', False)))

        # タイムスタンプ設定
        point = point.time(timestamp)

        return point

    def run(self):
        """メインループ"""
        try:
            self.connect_kafka()
            self.connect_influxdb()

            print("Started consuming messages...")
            message_count = 0

            for message in self.consumer:
                try:
                    point = self.process_message(message)
                    self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)

                    message_count += 1
                    if message_count % 10 == 0:
                        print(f"✓ Processed {message_count} messages")

                except Exception as e:
                    print(f"Error processing message: {e}")

        except KeyboardInterrupt:
            print("\nShutting down consumer...")
        finally:
            if self.consumer:
                self.consumer.close()
            if self.influx_client:
                self.influx_client.close()
            print("Consumer stopped")

if __name__ == '__main__':
    consumer = KafkaInfluxDBConsumer()
    consumer.run()
