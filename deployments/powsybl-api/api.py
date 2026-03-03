#!/usr/bin/env python3
"""
PowSyBl-like Power System Analysis API
電力系統解析APIのシンプル実装
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import os

app = FastAPI(title="Substation Analysis API", version="1.0.0")

# InfluxDB設定
INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb.data-zone.svc.cluster.local:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'substation')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'telemetry')

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
