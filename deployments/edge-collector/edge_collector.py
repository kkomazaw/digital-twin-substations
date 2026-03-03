#!/usr/bin/env python3
"""
Edge Data Collector (Redis版)
OT ZoneのIEDデータを受信し、中央Data Zone (Redis)へ転送
"""
import json
import socket
import os
import threading
from datetime import datetime
import redis

# 環境変数
LISTEN_HOST = os.environ.get('LISTEN_HOST', '0.0.0.0')
LISTEN_PORT = int(os.environ.get('LISTEN_PORT', '8888'))
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis.data-zone.svc.cluster.local')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_STREAM = os.environ.get('REDIS_STREAM', 'substation-telemetry')

class EdgeCollector:
    def __init__(self, listen_host, listen_port, redis_host, redis_port, redis_stream):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.redis_stream = redis_stream
        self.redis_client = None
        self.buffer = []
        self.buffer_lock = threading.Lock()

        # Redis接続初期化
        self.init_redis(redis_host, redis_port)

    def init_redis(self, host, port):
        """Redis接続初期化"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            print(f"✓ Connected to Redis: {host}:{port}")
        except Exception as e:
            print(f"✗ Failed to connect to Redis: {e}")
            print("  Running in buffer-only mode...")

    def handle_ied_connection(self, conn, addr):
        """IEDからの接続を処理"""
        print(f"Connection from {addr}")
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                # 改行区切りでメッセージを分割
                while b'\n' in data:
                    line, data = data.split(b'\n', 1)
                    if line:
                        self.process_message(line.decode('utf-8'))
        except Exception as e:
            print(f"Error handling connection from {addr}: {e}")
        finally:
            conn.close()

    def process_message(self, message):
        """受信したメッセージを処理"""
        try:
            data = json.loads(message)
            print(f"← Received from {data.get('station_id')}/{data.get('ied_id')}: "
                  f"F={data['measurements']['frequency']:.2f}Hz")

            # エッジでの前処理・フィルタリング
            enriched_data = self.enrich_data(data)

            # Redisに送信
            self.send_to_redis(enriched_data)

        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def enrich_data(self, data):
        """エッジでのデータエンリッチメント"""
        data['edge_timestamp'] = datetime.utcnow().isoformat() + 'Z'
        data['edge_collector'] = 'edge-collector-01'

        # 簡易的な異常検知
        freq = data['measurements']['frequency']
        if abs(freq - 50.0) > 1.0:
            data['status']['anomaly_detected'] = True
            data['status']['anomaly_type'] = 'frequency_deviation'
        else:
            data['status']['anomaly_detected'] = False

        return data

    def send_to_redis(self, data):
        """Redisにデータ送信（Streams使用）"""
        if self.redis_client is None:
            # Redisが利用できない場合はバッファに保存
            with self.buffer_lock:
                self.buffer.append(data)
                print(f"  Buffered (total: {len(self.buffer)})")
            return

        try:
            # Redis Streamsに追加
            message_id = self.redis_client.xadd(
                self.redis_stream,
                {'data': json.dumps(data)},
                maxlen=10000  # 最大10000件保持
            )
            print(f"→ Sent to Redis stream '{self.redis_stream}' (ID: {message_id.decode()})")
        except Exception as e:
            print(f"✗ Redis error: {e}")
            with self.buffer_lock:
                self.buffer.append(data)

    def run(self):
        """サーバー起動"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.listen_host, self.listen_port))
            server_socket.listen(5)
            print(f"Edge Collector listening on {self.listen_host}:{self.listen_port}")
            print(f"Forwarding to Redis stream: {self.redis_stream}")

            while True:
                try:
                    conn, addr = server_socket.accept()
                    # 各接続を別スレッドで処理
                    thread = threading.Thread(
                        target=self.handle_ied_connection,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                except KeyboardInterrupt:
                    print("\nShutting down Edge Collector...")
                    break
                except Exception as e:
                    print(f"Error accepting connection: {e}")

        if self.redis_client:
            self.redis_client.close()

if __name__ == '__main__':
    collector = EdgeCollector(LISTEN_HOST, LISTEN_PORT, REDIS_HOST, REDIS_PORT, REDIS_STREAM)
    collector.run()
