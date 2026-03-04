#!/usr/bin/env python3
"""
PowSyBl-like Power System Analysis API
電力系統解析APIのシンプル実装
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import os
import redis

app = FastAPI(title="Substation Analysis API", version="1.0.0")

# InfluxDB設定
INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb.data-zone.svc.cluster.local:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'substation')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'telemetry')

# Redis設定（トポロジー情報取得用）
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis.data-zone.svc.cluster.local')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))

class HealthStatus(BaseModel):
    status: str
    timestamp: str

class StationMetrics(BaseModel):
    station_id: str
    timestamp: str
    avg_voltage: float
    avg_current: float
    avg_frequency: float
    avg_active_power: float
    avg_reactive_power: float
    alarm_count: int

class AnomalyDetection(BaseModel):
    station_id: str
    timestamp: str
    anomaly_score: float
    anomaly_type: Optional[str]
    details: dict

class TopologyNode(BaseModel):
    id: str
    title: str
    mainStat: str
    secondaryStat: Optional[str] = None
    arc__healthy: float  # 0.0-1.0

class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    mainStat: str
    secondaryStat: Optional[str] = None

class TopologyGraph(BaseModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]

@app.get("/", response_model=HealthStatus)
async def root():
    """API ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/stations", response_model=List[str])
async def list_stations():
    """変電所リスト取得"""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "substation_telemetry")
          |> keep(columns: ["station_id"])
          |> distinct(column: "station_id")
        '''

        result = query_api.query(query=query)
        stations = []
        for table in result:
            for record in table.records:
                station_id = record.values.get("station_id")
                if station_id and station_id not in stations:
                    stations.append(station_id)

        client.close()
        return stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query stations: {str(e)}")

@app.get("/stations/{station_id}/metrics", response_model=StationMetrics)
async def get_station_metrics(station_id: str, duration: str = "5m"):
    """変電所の直近メトリクス取得"""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{duration})
          |> filter(fn: (r) => r["_measurement"] == "substation_telemetry")
          |> filter(fn: (r) => r["station_id"] == "{station_id}")
        '''

        result = query_api.query(query=query)

        # メトリクス集計
        metrics = {
            'voltage_a': [],
            'current_a': [],
            'frequency': [],
            'active_power': [],
            'reactive_power': [],
            'alarm': []
        }

        for table in result:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                if field in metrics:
                    metrics[field].append(value)

        client.close()

        # 平均計算
        avg_voltage = sum(metrics['voltage_a']) / len(metrics['voltage_a']) if metrics['voltage_a'] else 0
        avg_current = sum(metrics['current_a']) / len(metrics['current_a']) if metrics['current_a'] else 0
        avg_frequency = sum(metrics['frequency']) / len(metrics['frequency']) if metrics['frequency'] else 0
        avg_active_power = sum(metrics['active_power']) / len(metrics['active_power']) if metrics['active_power'] else 0
        avg_reactive_power = sum(metrics['reactive_power']) / len(metrics['reactive_power']) if metrics['reactive_power'] else 0
        alarm_count = sum(metrics['alarm']) if metrics['alarm'] else 0

        return StationMetrics(
            station_id=station_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            avg_voltage=abs(avg_voltage),
            avg_current=abs(avg_current),
            avg_frequency=avg_frequency,
            avg_active_power=avg_active_power,
            avg_reactive_power=avg_reactive_power,
            alarm_count=int(alarm_count)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/stations/{station_id}/anomalies", response_model=List[AnomalyDetection])
async def detect_anomalies(station_id: str, duration: str = "1h"):
    """異常検知"""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{duration})
          |> filter(fn: (r) => r["_measurement"] == "substation_telemetry")
          |> filter(fn: (r) => r["station_id"] == "{station_id}")
          |> filter(fn: (r) => r["_field"] == "anomaly_detected")
          |> filter(fn: (r) => r["_value"] == 1.0)
        '''

        result = query_api.query(query=query)
        anomalies = []

        for table in result:
            for record in table.records:
                anomalies.append(AnomalyDetection(
                    station_id=station_id,
                    timestamp=record.get_time().isoformat(),
                    anomaly_score=1.0,
                    anomaly_type="frequency_deviation",
                    details={
                        "ied_id": record.values.get("ied_id", "unknown"),
                        "type": record.values.get("type", "unknown")
                    }
                ))

        client.close()
        return anomalies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {str(e)}")

@app.get("/topology", response_model=TopologyGraph)
async def get_topology():
    """
    データフロートポロジーを取得（Grafana Node Graph Panel用）
    """
    try:
        # InfluxDBから最新メトリクスを取得
        influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = influx_client.query_api()

        # 過去1分間のIEDデータ取得
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1m)
          |> filter(fn: (r) => r["_measurement"] == "substation_telemetry")
          |> filter(fn: (r) => r["_field"] == "current_a" or r["_field"] == "alarm")
          |> last()
        '''

        result = query_api.query(query=query)

        # IEDごとのメトリクス集計
        ied_metrics = {}
        for table in result:
            for record in table.records:
                ied_id = record.values.get("ied_id", "unknown")
                field = record.get_field()
                value = record.get_value()

                if ied_id not in ied_metrics:
                    ied_metrics[ied_id] = {}
                ied_metrics[ied_id][field] = value

        influx_client.close()

        # Redisからストリーム統計取得
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        fledge_stream_len = redis_client.xlen('fledge-telemetry') if redis_client.exists('fledge-telemetry') else 0
        edge_stream_len = redis_client.xlen('substation-telemetry') if redis_client.exists('substation-telemetry') else 0
        redis_client.close()

        # ノード定義
        nodes = []
        edges = []

        # IEDノード
        for ied_id, metrics in ied_metrics.items():
            current = metrics.get('current_a', 0)
            alarm = metrics.get('alarm', 0)
            health = 0.0 if alarm > 0 else 1.0

            nodes.append(TopologyNode(
                id=ied_id,
                title=ied_id,
                mainStat=f"{abs(current):.1f}A",
                secondaryStat="OT Zone",
                arc__healthy=health
            ))

            # IED → FledgePOWER エッジ
            edges.append(TopologyEdge(
                id=f"{ied_id}-fledge",
                source=ied_id,
                target="fledgepower",
                mainStat="HTTP Poll",
                secondaryStat="1s interval"
            ))

            # IED → Edge Collector エッジ
            edges.append(TopologyEdge(
                id=f"{ied_id}-edge",
                source=ied_id,
                target="edge-collector",
                mainStat="TCP Push",
                secondaryStat="1s interval"
            ))

        # FledgePOWER Gateway ノード
        nodes.append(TopologyNode(
            id="fledgepower",
            title="FledgePOWER",
            mainStat=f"{fledge_stream_len} msgs",
            secondaryStat="Edge Zone",
            arc__healthy=1.0
        ))

        # Edge Collector ノード
        nodes.append(TopologyNode(
            id="edge-collector",
            title="Edge Collector",
            mainStat=f"{edge_stream_len} msgs",
            secondaryStat="Edge Zone",
            arc__healthy=1.0
        ))

        # Redis ノード
        total_msgs = fledge_stream_len + edge_stream_len
        nodes.append(TopologyNode(
            id="redis",
            title="Redis Streams",
            mainStat=f"{total_msgs} msgs",
            secondaryStat="Data Zone",
            arc__healthy=1.0
        ))

        # InfluxDB ノード
        nodes.append(TopologyNode(
            id="influxdb",
            title="InfluxDB",
            mainStat="Time-Series DB",
            secondaryStat="Data Zone",
            arc__healthy=1.0
        ))

        # Grafana ノード
        nodes.append(TopologyNode(
            id="grafana",
            title="Grafana",
            mainStat="Monitoring",
            secondaryStat="IT Zone",
            arc__healthy=1.0
        ))

        # Edge → Redis エッジ
        edges.append(TopologyEdge(
            id="fledge-redis",
            source="fledgepower",
            target="redis",
            mainStat="fledge-telemetry",
            secondaryStat=f"{fledge_stream_len} msgs"
        ))

        edges.append(TopologyEdge(
            id="edge-redis",
            source="edge-collector",
            target="redis",
            mainStat="substation-telemetry",
            secondaryStat=f"{edge_stream_len} msgs"
        ))

        # Redis → InfluxDB エッジ
        edges.append(TopologyEdge(
            id="redis-influxdb",
            source="redis",
            target="influxdb",
            mainStat="Consumers",
            secondaryStat="Dual streams"
        ))

        # InfluxDB → Grafana エッジ
        edges.append(TopologyEdge(
            id="influxdb-grafana",
            source="influxdb",
            target="grafana",
            mainStat="Flux Query",
            secondaryStat="Real-time"
        ))

        return TopologyGraph(nodes=nodes, edges=edges)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topology: {str(e)}")


# ============================================================================
# PowSyBl-like Advanced Analysis Endpoints (Mock Implementation)
# ============================================================================

# Analysis models
class LoadFlowRequest(BaseModel):
    network_id: str = "ieee14"
    parameters: Optional[Dict[str, Any]] = None

class LoadFlowResult(BaseModel):
    timestamp: str
    network_id: str
    convergence_status: str
    iterations: int
    computation_time_ms: float
    buses: List[Dict[str, Any]]
    branches: List[Dict[str, Any]]
    losses: Dict[str, float]

class SecurityAnalysisRequest(BaseModel):
    network_id: str = "ieee14"
    contingencies: List[Dict[str, Any]]

class SecurityAnalysisResult(BaseModel):
    timestamp: str
    network_id: str
    summary: Dict[str, int]

class SensitivityAnalysisRequest(BaseModel):
    network_id: str = "ieee14"
    factors: List[Dict[str, Any]]
    analysis_type: str = "DC"

class SensitivityAnalysisResult(BaseModel):
    timestamp: str
    network_id: str
    factor_count: int
    computation_time_ms: float


def generate_ieee14_mock_data():
    """IEEE 14バスシステムのモックデータを生成"""
    import random
    random.seed(42)

    # 14個のバス（母線）データ
    buses = []
    base_voltage = [1.060, 1.045, 1.010, 1.019, 1.020, 1.070, 1.062, 1.090,
                   1.056, 1.051, 1.057, 1.055, 1.050, 1.036]

    for i in range(14):
        buses.append({
            "id": f"Bus{i+1}",
            "voltage_magnitude": base_voltage[i] + random.uniform(-0.02, 0.02),
            "voltage_angle": random.uniform(-15, 15)
        })

    # 20個のブランチ（送電線）データ
    branches = []
    branch_configs = [
        ("L1-2-1", 1, 2, 152.9, 75.5),
        ("L1-5-1", 1, 5, 75.6, 18.4),
        ("L2-3-1", 2, 3, 73.2, 3.6),
        ("L2-4-1", 2, 4, 56.1, -1.6),
        ("L2-5-1", 2, 5, 41.5, 1.2),
        ("L3-4-1", 3, 4, -23.3, 2.4),
        ("L4-5-1", 4, 5, -61.2, 15.8),
        ("L4-7-1", 4, 7, 28.1, -9.7),
        ("L4-9-1", 4, 9, 16.1, 0.8),
        ("L5-6-1", 5, 6, 44.1, 12.5),
        ("L6-11-1", 6, 11, 7.4, 3.6),
        ("L6-12-1", 6, 12, 7.8, 2.5),
        ("L6-13-1", 6, 13, 17.7, 5.8),
        ("L7-8-1", 7, 8, 0.0, -17.4),
        ("L7-9-1", 7, 9, 28.1, 5.8),
        ("L9-10-1", 9, 10, 5.2, 4.2),
        ("L9-14-1", 9, 14, 9.4, 3.6),
        ("L10-11-1", 10, 11, -3.8, 1.8),
        ("L12-13-1", 12, 13, 1.6, 0.8),
        ("L13-14-1", 13, 14, 5.6, 1.8)
    ]

    for line_id, from_bus, to_bus, p_base, q_base in branch_configs:
        p_from = p_base + random.uniform(-5, 5)
        p_to = -p_from + random.uniform(-2, 2)  # 損失を考慮
        loading = abs(p_from) / 200.0 * 100  # 容量200MWと仮定

        branches.append({
            "id": line_id,
            "from_bus": f"Bus{from_bus}",
            "to_bus": f"Bus{to_bus}",
            "active_power_from": round(p_from, 2),
            "active_power_to": round(p_to, 2),
            "reactive_power_from": round(q_base + random.uniform(-2, 2), 2),
            "reactive_power_to": round(-q_base + random.uniform(-2, 2), 2),
            "loading": round(min(loading, 99.5), 1)
        })

    return buses, branches


@app.get("/api/v1/loadflow", response_model=LoadFlowResult)
@app.post("/api/v1/loadflow", response_model=LoadFlowResult)
async def run_loadflow(request: Optional[LoadFlowRequest] = None, network_id: str = "default"):
    """
    潮流計算を実行（モック実装）
    GETとPOSTの両方をサポート
    """
    import time
    start_time = time.time()

    try:
        buses, branches = generate_ieee14_mock_data()

        # 損失計算
        total_active_loss = sum(
            abs(b["active_power_from"] + b["active_power_to"])
            for b in branches
        )
        total_reactive_loss = sum(
            abs(b["reactive_power_from"] + b["reactive_power_to"])
            for b in branches
        )

        computation_time = (time.time() - start_time) * 1000

        # リクエストからnetwork_idを取得（POSTの場合はrequestから、GETの場合はクエリパラメータから）
        nw_id = request.network_id if request else network_id

        return LoadFlowResult(
            timestamp=datetime.utcnow().isoformat() + "Z",
            network_id=nw_id,
            convergence_status="CONVERGED",
            iterations=4,
            computation_time_ms=round(computation_time, 2),
            buses=buses,
            branches=branches,
            losses={
                "active_power": round(total_active_loss, 2),
                "reactive_power": round(total_reactive_loss, 2)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load flow failed: {str(e)}")


@app.get("/api/v1/security", response_model=SecurityAnalysisResult)
@app.post("/api/v1/security", response_model=SecurityAnalysisResult)
async def run_security_analysis(request: Optional[SecurityAnalysisRequest] = None, network_id: str = "default"):
    """
    セキュリティ分析を実行（N-1分析）（モック実装）
    GETとPOSTの両方をサポート
    """
    import time
    import random
    random.seed(42)

    start_time = time.time()

    try:
        # コンティンジェンシー数
        total_contingencies = 5
        if request and request.contingencies:
            total_contingencies = len(request.contingencies)

        # モック結果生成
        critical_violations = random.randint(0, 2)
        failed_contingencies = random.randint(0, 1)

        computation_time = (time.time() - start_time) * 1000

        nw_id = request.network_id if request else network_id

        return SecurityAnalysisResult(
            timestamp=datetime.utcnow().isoformat() + "Z",
            network_id=nw_id,
            summary={
                "total_contingencies": total_contingencies,
                "critical_violations": critical_violations,
                "failed_contingencies": failed_contingencies,
                "computation_time_ms": int(round(computation_time, 0))
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Security analysis failed: {str(e)}")


@app.get("/api/v1/sensitivity", response_model=SensitivityAnalysisResult)
@app.post("/api/v1/sensitivity", response_model=SensitivityAnalysisResult)
async def run_sensitivity_analysis(request: Optional[SensitivityAnalysisRequest] = None, network_id: str = "default"):
    """
    感度分析を実行（モック実装）
    GETとPOSTの両方をサポート
    """
    import time
    start_time = time.time()

    try:
        # モック係数行列サイズ
        factor_count = 9
        if request and request.factors:
            factor_count = len(request.factors)

        computation_time = (time.time() - start_time) * 1000

        nw_id = request.network_id if request else network_id

        return SensitivityAnalysisResult(
            timestamp=datetime.utcnow().isoformat() + "Z",
            network_id=nw_id,
            factor_count=factor_count,
            computation_time_ms=round(computation_time, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sensitivity analysis failed: {str(e)}")


@app.get("/api/v1/networks")
async def list_networks():
    """利用可能なネットワークリスト"""
    return {
        "networks": ["ieee14"],
        "description": "Mock implementation - IEEE 14 bus test system"
    }


class NetworkTopologyNode(BaseModel):
    id: str
    title: str
    subTitle: str
    mainStat: str
    secondaryStat: Optional[str] = None
    arc__success: float  # 0.0-1.0
    arc__failed: float = 0.0
    arc__warning: float = 0.0

class NetworkTopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    mainStat: str
    secondaryStat: Optional[str] = None
    strength: float = 1.0  # Line loading indicator

class NetworkTopology(BaseModel):
    nodes: List[NetworkTopologyNode]
    edges: List[NetworkTopologyEdge]


@app.get("/api/v1/network/topology", response_model=NetworkTopology)
async def get_network_topology(network_id: str = "ieee14"):
    """
    IEEE 14バスシステムのネットワークトポロジーを取得
    PowSyBl Network Area Diagram形式に準拠
    """
    try:
        # IEEE 14バスのトポロジーデータを生成
        buses, branches = generate_ieee14_mock_data()

        nodes = []
        edges = []

        # ノード（バス）の定義
        # IEEE 14バスシステム：Bus1-Bus5が138kV、Bus6-Bus14が69kV
        voltage_levels = {
            "Bus1": "138kV", "Bus2": "138kV", "Bus3": "138kV", "Bus4": "138kV", "Bus5": "138kV",
            "Bus6": "69kV", "Bus7": "69kV", "Bus8": "69kV", "Bus9": "69kV", "Bus10": "69kV",
            "Bus11": "69kV", "Bus12": "69kV", "Bus13": "69kV", "Bus14": "69kV"
        }

        # 発電機バス（Generator Buses）
        generator_buses = ["Bus1", "Bus2", "Bus3", "Bus6", "Bus8"]

        for bus in buses:
            bus_id = bus["id"]
            voltage_mag = bus["voltage_magnitude"]
            voltage_angle = bus["voltage_angle"]

            # 電圧レベルに基づいて健全性を計算
            base_voltage = 138.0 if voltage_levels[bus_id] == "138kV" else 69.0
            voltage_actual = voltage_mag * base_voltage
            voltage_deviation = abs(voltage_mag - 1.0)

            # 健全性スコア（電圧偏差が小さいほど高い）
            health = max(0.0, min(1.0, 1.0 - voltage_deviation * 10))

            bus_type = "Gen" if bus_id in generator_buses else "Load"

            nodes.append(NetworkTopologyNode(
                id=bus_id,
                title=bus_id,
                subTitle=f"{voltage_levels[bus_id]} {bus_type}",
                mainStat=f"{voltage_mag:.3f} pu",
                secondaryStat=f"{voltage_angle:.1f}°",
                arc__success=health,
                arc__failed=0.0 if health > 0.95 else (1.0 - health) * 0.5,
                arc__warning=0.0 if health > 0.95 else (1.0 - health) * 0.5
            ))

        # エッジ（ライン）の定義
        for branch in branches:
            line_id = branch["id"]
            from_bus = branch["from_bus"]
            to_bus = branch["to_bus"]
            loading = branch["loading"]
            p_from = branch["active_power_from"]

            # ライン負荷に基づいて強度を設定
            strength = min(1.0, loading / 50.0)  # 50%負荷を基準

            # 負荷状態の判定
            if loading > 90:
                status = "Critical"
            elif loading > 70:
                status = "High"
            else:
                status = "Normal"

            edges.append(NetworkTopologyEdge(
                id=line_id,
                source=from_bus,
                target=to_bus,
                mainStat=f"{abs(p_from):.1f} MW",
                secondaryStat=f"{loading:.1f}% ({status})",
                strength=strength
            ))

        return NetworkTopology(nodes=nodes, edges=edges)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topology: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
