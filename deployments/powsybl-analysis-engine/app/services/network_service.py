"""
Network Service
ネットワークモデル管理サービス
"""
import pypowsybl as pp
import pypowsybl.network as pn
from typing import Optional, Dict, Any
from datetime import datetime
from influxdb_client import InfluxDBClient
import redis
import os
import logging

logger = logging.getLogger(__name__)


class NetworkService:
    """ネットワークモデル管理サービス"""

    def __init__(self):
        self.networks: Dict[str, pn.Network] = {}

        # InfluxDB設定
        self.influxdb_url = os.environ.get('INFLUXDB_URL', 'http://influxdb.data-zone.svc.cluster.local:8086')
        self.influxdb_token = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
        self.influxdb_org = os.environ.get('INFLUXDB_ORG', 'substation')
        self.influxdb_bucket = os.environ.get('INFLUXDB_BUCKET', 'telemetry')

        # Redis設定
        self.redis_host = os.environ.get('REDIS_HOST', 'redis.data-zone.svc.cluster.local')
        self.redis_port = int(os.environ.get('REDIS_PORT', '6379'))

    def create_sample_network(self, network_id: str = "sample_network") -> pn.Network:
        """
        サンプルネットワークを作成（デモ・テスト用）
        IEEE 14 busシステムベース
        """
        network = pp.network.create_ieee14()
        self.networks[network_id] = network
        logger.info(f"Sample network created: {network_id}")
        return network

    def create_network_from_telemetry(self, network_id: str, station_ids: list) -> pn.Network:
        """
        テレメトリーデータからネットワークモデルを構築
        """
        try:
            # 空のネットワークを作成
            network = pp.network.create_empty(network_id)

            # InfluxDBから最新データを取得
            client = InfluxDBClient(url=self.influxdb_url, token=self.influxdb_token, org=self.influxdb_org)
            query_api = client.query_api()

            # 各変電所のデータを取得してネットワークに追加
            for station_id in station_ids:
                query = f'''
                from(bucket: "{self.influxdb_bucket}")
                  |> range(start: -5m)
                  |> filter(fn: (r) => r["_measurement"] == "substation_telemetry")
                  |> filter(fn: (r) => r["station_id"] == "{station_id}")
                  |> last()
                '''

                result = query_api.query(query=query)

                # データからネットワーク要素を構築
                # （実際のプロジェクトではIED/変電所の構成に応じて実装）
                telemetry_data = self._parse_telemetry_result(result)
                self._build_network_elements(network, station_id, telemetry_data)

            client.close()
            self.networks[network_id] = network
            logger.info(f"Network created from telemetry: {network_id}")
            return network

        except Exception as e:
            logger.error(f"Failed to create network from telemetry: {e}")
            raise

    def _parse_telemetry_result(self, result) -> Dict[str, Any]:
        """テレメトリー結果をパース"""
        data = {}
        for table in result:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                data[field] = value
        return data

    def _build_network_elements(self, network: pn.Network, station_id: str, telemetry: Dict):
        """
        テレメトリーデータからネットワーク要素を構築
        簡易実装：各変電所をバス+発電機+負荷として表現
        """
        # 電圧レベル（例：22kV）
        voltage_level = telemetry.get('voltage_a', 22000)

        # サブステーション追加
        network.create_substations(id=station_id, name=f"Substation {station_id}")

        # 電圧レベル追加
        vl_id = f"{station_id}_VL"
        network.create_voltage_levels(
            id=vl_id,
            substation_id=station_id,
            topology_kind='BUS_BREAKER',
            nominal_v=voltage_level / 1000.0  # kV単位
        )

        # バス追加
        bus_id = f"{station_id}_BUS"
        network.create_buses(id=bus_id, voltage_level_id=vl_id)

        # 発電機追加（有効電力がプラスの場合）
        active_power = telemetry.get('active_power', 0)
        if active_power > 0:
            network.create_generators(
                id=f"{station_id}_GEN",
                bus_id=bus_id,
                min_p=0,
                max_p=active_power * 2,
                target_p=active_power,
                target_v=voltage_level / 1000.0,
                voltage_regulator_on=True
            )

        # 負荷追加（有効電力がマイナスの場合）
        elif active_power < 0:
            reactive_power = telemetry.get('reactive_power', 0)
            network.create_loads(
                id=f"{station_id}_LOAD",
                bus_id=bus_id,
                p0=abs(active_power),
                q0=abs(reactive_power)
            )

    def get_network(self, network_id: str) -> Optional[pn.Network]:
        """ネットワークを取得"""
        return self.networks.get(network_id)

    def load_network_from_file(self, network_id: str, file_path: str) -> pn.Network:
        """
        ファイルからネットワークをロード
        対応フォーマット: IIDM, UCTE, CIM, MATPOWER等
        """
        network = pp.network.load(file_path)
        self.networks[network_id] = network
        logger.info(f"Network loaded from file: {network_id}")
        return network

    def export_network(self, network_id: str, file_path: str, format: str = "XIIDM"):
        """ネットワークをエクスポート"""
        network = self.get_network(network_id)
        if network:
            network.dump(file_path, format=format)
            logger.info(f"Network exported: {network_id} -> {file_path}")
        else:
            raise ValueError(f"Network not found: {network_id}")

    def get_network_info(self, network_id: str) -> Dict[str, Any]:
        """ネットワーク情報を取得"""
        network = self.get_network(network_id)
        if not network:
            raise ValueError(f"Network not found: {network_id}")

        return {
            "network_id": network_id,
            "name": network.name,
            "bus_count": len(network.get_buses()),
            "line_count": len(network.get_lines()),
            "generator_count": len(network.get_generators()),
            "load_count": len(network.get_loads()),
            "transformer_count": len(network.get_2_windings_transformers()),
            "substation_count": len(network.get_substations())
        }
