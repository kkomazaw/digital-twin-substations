#!/usr/bin/env python3
"""
Redis to InfluxDB Consumer
Redisから変電所テレメトリデータを受信しInfluxDBに書き込む
"""
import json
import os
from datetime import datetime
import redis
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import time

# 環境変数
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis.data-zone.svc.cluster.local')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_STREAM = os.environ.get('REDIS_STREAM', 'substation-telemetry')
REDIS_CONSUMER_GROUP = os.environ.get('REDIS_CONSUMER_GROUP', 'influxdb-consumers')
REDIS_CONSUMER_NAME = os.environ.get('REDIS_CONSUMER_NAME', 'consumer-1')

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb.data-zone.svc.cluster.local:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'substation')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'telemetry')

class RedisInfluxDBConsumer:
    def __init__(self):
        self.redis_client = None
        self.influx_client = None
        self.write_api = None

    def connect_redis(self):
        """Redis接続"""
        print(f"Connecting to Redis: {REDIS_HOST}:{REDIS_PORT}")
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False
        )
        self.redis_client.ping()
        print(f"✓ Connected to Redis")

        # Consumer Groupを作成（既存の場合はエラーを無視）
        try:
            self.redis_client.xgroup_create(
                REDIS_STREAM,
                REDIS_CONSUMER_GROUP,
                id='0',
                mkstream=True
            )
            print(f"✓ Created consumer group: {REDIS_CONSUMER_GROUP}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                print(f"  Consumer group already exists: {REDIS_CONSUMER_GROUP}")
            else:
                raise

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

    def process_message(self, message_id, message_data):
        """メッセージをInfluxDBポイントに変換"""
        try:
            # Redis Streamのメッセージからデータを取得
            data_json = message_data.get(b'data')
            if not data_json:
                return None

            data = json.loads(data_json.decode('utf-8'))

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
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")
            return None

    def run(self):
        """メインループ"""
        try:
            self.connect_redis()
            self.connect_influxdb()

            print(f"Started consuming from stream '{REDIS_STREAM}'...")
            message_count = 0

            while True:
                try:
                    # Redis Streamから読み取り（Consumer Group使用）
                    messages = self.redis_client.xreadgroup(
                        REDIS_CONSUMER_GROUP,
                        REDIS_CONSUMER_NAME,
                        {REDIS_STREAM: '>'},
                        count=10,
                        block=1000  # 1秒待機
                    )

                    if not messages:
                        continue

                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            point = self.process_message(message_id, message_data)

                            if point:
                                self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
                                message_count += 1

                                if message_count % 10 == 0:
                                    print(f"✓ Processed {message_count} messages")

                            # メッセージを確認（ACK）
                            self.redis_client.xack(REDIS_STREAM, REDIS_CONSUMER_GROUP, message_id)

                except redis.exceptions.RedisError as e:
                    print(f"Redis error: {e}")
                    time.sleep(5)
                except Exception as e:
                    print(f"Error in consumer loop: {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down consumer...")
        finally:
            if self.redis_client:
                self.redis_client.close()
            if self.influx_client:
                self.influx_client.close()
            print("Consumer stopped")

if __name__ == '__main__':
    consumer = RedisInfluxDBConsumer()
    consumer.run()
