#!/usr/bin/env python3
"""
IED HTTP Server for FledgePOWER
HTTPエンドポイントを提供し、Fledgeからのポーリングに対応
"""
import json
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from ied_simulator import IEDSimulator

# 環境変数から設定取得
STATION_ID = os.environ.get('STATION_ID', 'station-a')
IED_ID = os.environ.get('IED_ID', socket.gethostname())
HTTP_PORT = int(os.environ.get('HTTP_PORT', '8080'))

# グローバル変数でIEDシミュレータを保持
simulator = IEDSimulator(STATION_ID, IED_ID)
latest_data = None
data_lock = threading.Lock()


class IEDHTTPHandler(BaseHTTPRequestHandler):
    """IEDデータを返すHTTPリクエストハンドラ"""

    def log_message(self, format, *args):
        """ログ出力を簡略化"""
        pass  # 標準出力への自動ログを抑制

    def do_GET(self):
        """GETリクエスト処理"""
        global latest_data

        if self.path == '/telemetry':
            # 最新の計測データを返す
            with data_lock:
                if latest_data:
                    data = latest_data
                else:
                    # データがない場合は新規生成
                    data = simulator.generate_sv_data()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))

        elif self.path == '/health':
            # ヘルスチェック
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'station_id': STATION_ID,
                'ied_id': IED_ID,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/':
            # ルートパス - API情報
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'service': 'IED HTTP Server',
                'station_id': STATION_ID,
                'ied_id': IED_ID,
                'endpoints': {
                    '/telemetry': 'Get latest telemetry data',
                    '/health': 'Health check'
                }
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()


def data_generator():
    """
    バックグラウンドでデータを生成し続ける
    最新データをlatest_dataに保存
    """
    global latest_data
    import time

    print(f"Data generator started for {STATION_ID}/{IED_ID}")

    while True:
        try:
            data = simulator.generate_sv_data()

            with data_lock:
                latest_data = data

            time.sleep(1.0)  # 1秒ごとにデータ更新

        except Exception as e:
            print(f"Error generating data: {e}")
            time.sleep(1.0)


def run_server():
    """HTTPサーバー起動"""
    import socket as sock

    server_address = ('', HTTP_PORT)
    httpd = HTTPServer(server_address, IEDHTTPHandler)

    print(f"IED HTTP Server started on port {HTTP_PORT}")
    print(f"Station: {STATION_ID}, IED: {IED_ID}")
    print(f"Endpoints:")
    print(f"  http://localhost:{HTTP_PORT}/telemetry")
    print(f"  http://localhost:{HTTP_PORT}/health")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down HTTP server...")
        httpd.shutdown()


if __name__ == '__main__':
    import socket

    # バックグラウンドでデータ生成開始
    data_thread = threading.Thread(target=data_generator, daemon=True)
    data_thread.start()

    # HTTPサーバー起動（メインスレッド）
    run_server()
