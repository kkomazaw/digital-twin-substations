# FledgePOWER Gateway

FledgePOWER-based gateway for IEC 61850 protocol handling in digital twin substation.

## Architecture

```
IED Simulators (OT Zone)
         ↓ HTTP/REST (初期実装) or IEC 61850 MMS (将来)
FledgePOWER Gateway (Edge Zone)
  - South Plugin: HTTP Polling / IEC 61850
  - Filters: Data Quality, Transformation
  - North Plugin: Redis Streams
         ↓
Redis Streams (Data Zone)
  - Stream: "fledge-telemetry"
         ↓
InfluxDB Consumer
         ↓
InfluxDB / Grafana
```

## Components

### South Plugins
1. **HTTP Polling** (`fledge-south-http`)
   - Poll IED simulators via HTTP/REST
   - Default: 1 second interval
   - Endpoint: `http://ied-simulator.ot-zone:8080/telemetry`

2. **IEC 61850 MMS** (Future)
   - Native IEC 61850 protocol support
   - Port 102 communication
   - Dataset subscription

### North Plugins
1. **Redis Streams** (`fledge-north-redis`)
   - Send data to Redis Streams
   - Stream name: `fledge-telemetry`
   - Max length: 10,000 messages
   - Batch processing for efficiency

## Configuration

### South Plugin Example (HTTP)
```json
{
  "asset_name": "substation_telemetry",
  "url": "http://ied-simulator.ot-zone.svc.cluster.local:8080/telemetry",
  "poll_interval": 1,
  "timeout": 5
}
```

### North Plugin Example (Redis)
```json
{
  "host": "redis.data-zone.svc.cluster.local",
  "port": 6379,
  "stream_name": "fledge-telemetry",
  "max_length": 10000,
  "source": "fledgepower"
}
```

## Resource Requirements

- CPU: 500m (request: 250m)
- Memory: 512Mi (request: 256Mi)
- Storage: 10Gi PVC for local buffering

## Security

- NetworkPolicy: Only allow connections from OT Zone (ingress) and to Data Zone (egress)
- Read-only filesystem except for data directory
- Non-root user (fledge:fledge)

## Monitoring

- Fledge GUI: Port 8081
- Management API: Port 1995
- MQTT (optional): Port 6683

## Development

### Build Container
```bash
cd deployments/fledgepower-gateway
podman build -t fledgepower-gateway:latest .
```

### Test Locally
```bash
podman run -p 8081:8081 -p 1995:1995 \
  -e FLEDGE_SOUTH_URL=http://localhost:8888 \
  -e FLEDGE_REDIS_HOST=localhost \
  fledgepower-gateway:latest
```

## Future Enhancements

1. **IEC 61850 MMS Support**
   - Integrate libiec61850 or official Fledge IEC 61850 plugin
   - Support GOOSE and Sampled Values

2. **Advanced Filtering**
   - Data quality checks (IEC 61850 quality bits)
   - Outlier detection
   - Data compression

3. **Local Analytics**
   - Edge anomaly detection
   - Predictive maintenance
   - Real-time alerting

4. **High Availability**
   - Multiple Fledge instances
   - Redis Sentinel integration
   - Failover mechanisms
