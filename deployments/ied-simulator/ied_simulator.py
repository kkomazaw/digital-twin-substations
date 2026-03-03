#!/usr/bin/env python3
"""
IED (Intelligent Electronic Device) Simulator
変電所のIEDデバイスをシミュレートし、計測データ(SV)を生成
"""
import json
import time
import random
import math
import socket
import os
from datetime import datetime

# 環境変数から設定取得
STATION_ID = os.environ.get('STATION_ID', 'station-a')
IED_ID = os.environ.get('IED_ID', 'ied-01')
DATA_INTERVAL = float(os.environ.get('DATA_INTERVAL', '1.0'))  # 秒
OUTPUT_HOST = os.environ.get('OUTPUT_HOST', 'edge-collector')
OUTPUT_PORT = int(os.environ.get('OUTPUT_PORT', '8888'))

class IEDSimulator:
    def __init__(self, station_id, ied_id):
        self.station_id = station_id
        self.ied_id = ied_id
        self.base_voltage = 154000  # 154kV
        self.base_current = 1000    # 1000A
        self.base_frequency = 50.0  # 50Hz
        self.time_offset = 0

    def generate_sv_data(self):
        """
        Sampled Values (SV) データを生成
        IEC 61850-9-2 準拠のシミュレーション
        """
        current_time = time.time()

        # 正弦波ベースの電圧・電流データ生成（3相）
        angle = (current_time + self.time_offset) * 2 * math.pi * self.base_frequency

        # わずかな揺らぎを追加
        voltage_variation = random.uniform(0.98, 1.02)
        current_variation = random.uniform(0.95, 1.05)
        frequency_variation = random.uniform(-0.1, 0.1)

        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'station_id': self.station_id,
            'ied_id': self.ied_id,
            'type': 'SV',  # Sampled Values
            'measurements': {
                # 電圧 (3相)
                'voltage_a': self.base_voltage * voltage_variation * math.sin(angle),
                'voltage_b': self.base_voltage * voltage_variation * math.sin(angle - 2*math.pi/3),
                'voltage_c': self.base_voltage * voltage_variation * math.sin(angle + 2*math.pi/3),
                # 電流 (3相)
                'current_a': self.base_current * current_variation * math.sin(angle - math.pi/6),
                'current_b': self.base_current * current_variation * math.sin(angle - 2*math.pi/3 - math.pi/6),
                'current_c': self.base_current * current_variation * math.sin(angle + 2*math.pi/3 - math.pi/6),
                # 周波数
                'frequency': self.base_frequency + frequency_variation,
                # 電力計算
                'active_power': self.base_voltage * self.base_current * 0.95 * voltage_variation * current_variation,
                'reactive_power': self.base_voltage * self.base_current * 0.3 * voltage_variation * current_variation,
            },
            'status': {
                'healthy': True,
                'alarm': False,
                'protection_activated': False
            }
        }

        # ランダムに異常状態をシミュレート (5%の確率)
        if random.random() < 0.05:
            data['measurements']['frequency'] += random.choice([-2, 2])
            data['status']['alarm'] = True

        return data

    def send_to_edge(self, data):
        """エッジコレクターにデータ送信"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((OUTPUT_HOST, OUTPUT_PORT))
                message = json.dumps(data) + '\n'
                s.sendall(message.encode('utf-8'))
                print(f"✓ Sent data to {OUTPUT_HOST}:{OUTPUT_PORT}")
        except Exception as e:
            print(f"✗ Failed to send data: {e}")

    def run(self, interval=1.0):
        """シミュレーションメインループ"""
        print(f"IED Simulator started: {self.station_id}/{self.ied_id}")
        print(f"Sending data to {OUTPUT_HOST}:{OUTPUT_PORT} every {interval}s")

        while True:
            try:
                data = self.generate_sv_data()
                print(f"[{data['timestamp']}] V={data['measurements']['voltage_a']:.1f}V "
                      f"I={data['measurements']['current_a']:.1f}A "
                      f"F={data['measurements']['frequency']:.2f}Hz "
                      f"P={data['measurements']['active_power']:.1f}W")

                self.send_to_edge(data)
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nStopping IED simulator...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

if __name__ == '__main__':
    simulator = IEDSimulator(STATION_ID, IED_ID)
    simulator.run(DATA_INTERVAL)
