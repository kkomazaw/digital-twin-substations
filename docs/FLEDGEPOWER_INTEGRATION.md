# FledgePOWER統合設計書

## 概要

本ドキュメントは、デジタルツイン変電所デモにおけるFledgePOWERの統合設計を説明します。
**アプローチB（ハイブリッド設計）**を採用し、FledgePOWERとEdge Collectorを併用します。

## アーキテクチャ

### ハイブリッドデータフロー

```
┌─────────────────────────────────────────────────────────┐
│ OT Zone (IEC 62443 Level 0-2)                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ IED Simulator × 3                                 │   │
│  │  - HTTP Server (Port 8080): /telemetry, /health  │   │
│  │  - 3相電圧・電流・周波数データ生成                   │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────┬───────────────────────┬────────────────┘
                 │                       │
      ┌──────────▼─────────┐   ┌────────▼──────────┐
      │                    │   │                   │
┌─────┴──────────────────┐ │   │ ┌────────────────┴─────┐
│ Edge Zone - Path A     │ │   │ │ Edge Zone - Path B   │
│  FledgePOWER Gateway   │ │   │ │  Edge Collector      │
│  (プロダクション向け)      │ │   │ │  (レガシー/フォールバック)│
│                        │ │   │ │                      │
│  ┌──────────────────┐  │ │   │ │                      │
│  │ South Plugin:    │  │ │   │ │  - HTTP Push受信      │
│  │  HTTP Polling    │  │ │   │ │  - 異常検知            │
│  │  (1秒間隔)        │  │ │   │ │  - データ転送          │
│  └──────────────────┘  │ │   │ │                      │
│  ┌──────────────────┐  │ │   │ │                      │
│  │ Filters:         │  │ │   │ │                      │
│  │  - Data Quality  │  │ │   │ │                      │
│  │  - Transform     │  │ │   │ │                      │
│  └──────────────────┘  │ │   │ │                      │
│  ┌──────────────────┐  │ │   │ │                      │
│  │ North Plugin:    │  │ │   │ │                      │
│  │  Redis Streams   │  │ │   │ │                      │
│  └──────────────────┘  │ │   │ │                      │
└────────┬───────────────┘ │   │ └──────────┬───────────┘
         │                 │   │            │
         │ Stream:         │   │            │ Stream:
         │ "fledge-        │   │            │ "substation-
         │  telemetry"     │   │            │  telemetry"
         │                 │   │            │
┌────────▼─────────────────┴───┴────────────▼───────────┐
│ Data Zone                                             │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Redis Streams                                     │ │
│  │  - fledge-telemetry (FledgePOWER経由)             │ │
│  │  - substation-telemetry (Edge Collector経由)     │ │
│  └──────────────┬──────────────────┬────────────────┘ │
│                 │                  │                   │
│  ┌──────────────▼──────┐  ┌────────▼────────────────┐ │
│  │ Fledge Consumer     │  │ Redis Consumer          │ │
│  │ (高頻度データ)        │  │ (通常データ)             │ │
│  └──────────────┬──────┘  └────────┬────────────────┘ │
│                 │                  │                   │
│                 └──────────────────▼──────────┐        │
│                            InfluxDB          │        │
│                            - Bucket: telemetry│        │
│                            - 全データ統合保存  │        │
│                            └──────────────────┘        │
└───────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────┐
│ Application Zone                                      │
│  - PowSyBl API (電力系統解析)                           │
└───────────────────────────────┬───────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────┐
│ IT Zone                                               │
│  - Grafana (統合ダッシュボード)                          │
│    * Fledgeデータ品質モニタリング                        │
│    * 統合テレメトリ可視化                                │
└───────────────────────────────────────────────────────┘
```

## コンポーネント詳細

### 1. FledgePOWER Gateway

**場所**: `edge-zone` namespace

**機能**:
- IEC 61850プロトコルハンドリング（将来）
- HTTP Polling（現在実装）
- データ品質チェック
- プロトコル変換
- ローカルバッファリング（10Gi PVC）

**プラグイン**:

#### South Plugin: HTTP Polling
```json
{
  "asset_name": "substation_telemetry",
  "url": "http://ied-simulator.ot-zone.svc.cluster.local:8080/telemetry",
  "poll_interval": 1,
  "timeout": 5
}
```

#### North Plugin: Redis Streams
```json
{
  "host": "redis.data-zone.svc.cluster.local",
  "port": 6379,
  "stream_name": "fledge-telemetry",
  "max_length": 10000,
  "source": "fledgepower"
}
```

**リソース要件**:
- CPU: 500m (request: 250m)
- Memory: 512Mi (request: 256Mi)
- Storage: 10Gi PVC

**管理インターフェース**:
- GUI: Port 8081 (Route経由で公開)
- API: Port 1995
- MQTT: Port 6683 (オプション)

### 2. IED Simulator拡張

**新機能**: HTTPサーバー

**エンドポイント**:
- `GET /telemetry`: 最新の計測データを返す
- `GET /health`: ヘルスチェック
- `GET /`: API情報

**応答例** (`/telemetry`):
```json
{
  "timestamp": "2026-03-03T02:30:00.000000Z",
  "station_id": "station-a",
  "ied_id": "ied-simulator-xyz",
  "type": "SV",
  "measurements": {
    "voltage_a": 154234.5,
    "voltage_b": 153987.2,
    "voltage_c": 154123.8,
    "current_a": 1025.3,
    "current_b": 1018.7,
    "current_c": 1022.1,
    "frequency": 50.02,
    "active_power": 158750000.0,
    "reactive_power": 46125000.0
  },
  "status": {
    "healthy": true,
    "alarm": false,
    "protection_activated": false
  }
}
```

### 3. NetworkPolicy

**Fledge専用ポリシー** (`edge-zone-fledge-policy.yaml`):

```yaml
# Ingress: OT Zone（IED）とIT Zone（監視）から許可
ingress:
- from:
  - namespaceSelector:
      matchLabels:
        name: ot-zone
  ports:
  - protocol: TCP
    port: 8081  # GUI
  - protocol: TCP
    port: 1995  # API

# Egress: Data Zone（Redis）のみ許可
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: data-zone
  ports:
  - protocol: TCP
    port: 6379  # Redis
```

## デプロイ手順

### 1. イメージビルド

```bash
# FledgePOWER Gateway
cd /path/to/digital-twin-substations
./scripts/build-images-openshift.sh
# → fledgepower-gateway イメージビルド

# IED Simulator（HTTPサーバー対応版）
# → ied-simulator イメージ再ビルド
```

### 2. デプロイ

```bash
# 完全デプロイ（FledgePOWER含む）
./scripts/deploy-fledge.sh

# または個別デプロイ
oc apply -f openshift/edge-zone/fledgepower-deployment.yaml
oc apply -f k8s/network-policies/edge-zone-fledge-policy.yaml
```

### 3. 確認

```bash
# Pod状態確認
oc get pods -n edge-zone

# FledgePOWER GUI URLを取得
FLEDGE_URL=$(oc get route fledgepower-gui -n edge-zone -o jsonpath='{.spec.host}')
echo "FledgePOWER GUI: http://${FLEDGE_URL}"

# ログ確認
oc logs -n edge-zone -l app=fledgepower-gateway -f

# データフロー確認
# ① FledgePOWER → Redis
POD=$(oc get pod -n data-zone -l app=redis -o jsonpath='{.items[0].metadata.name}')
oc exec -n data-zone $POD -- redis-cli XLEN fledge-telemetry

# ② Edge Collector → Redis
oc exec -n data-zone $POD -- redis-cli XLEN substation-telemetry
```

## 運用

### モニタリング

#### FledgePOWER GUI
- URL: `http://fledgepower-gui-edge-zone.apps-crc.testing`
- 機能:
  - South/Northプラグイン状態
  - データフロー統計
  - エラーログ
  - 設定変更

#### Grafanaダッシュボード

新しいダッシュボード追加予定:
1. **Fledge Data Quality Monitor**
   - データ受信レート
   - プラグイン状態
   - エラー率

2. **Hybrid Data Flow Comparison**
   - Fledge vs Edge Collector比較
   - レイテンシ分析
   - スループット比較

### トラブルシューティング

#### Fledgeが起動しない

```bash
# PVC確認
oc get pvc -n edge-zone

# ログ確認
oc logs -n edge-zone deployment/fledgepower-gateway --previous

# 権限確認
oc adm policy add-scc-to-user anyuid -z default -n edge-zone
oc rollout restart deployment fledgepower-gateway -n edge-zone
```

#### データが流れない

```bash
# ① IED HTTPエンドポイント確認
oc exec -n edge-zone deployment/fledgepower-gateway -- \
  curl http://ied-simulator.ot-zone.svc.cluster.local:8080/telemetry

# ② Fledge South Plugin状態確認
# GUI → South → IED-HTTP-Poll → Status

# ③ Redis接続確認
oc exec -n edge-zone deployment/fledgepower-gateway -- \
  redis-cli -h redis.data-zone.svc.cluster.local ping
```

## 将来の拡張

### Phase 2: IEC 61850 MMS実装

```yaml
# IED Simulator に libiec61850 統合
south_plugin:
  plugin: "fledge-south-iec61850"
  config:
    protocol: "MMS"
    port: 102
    ied_address: "ied-simulator.ot-zone.svc.cluster.local"
    dataset: "LLN0$MX$MMXU1"
    datapoints:
      - "MMXU1.TotW"  # Active Power
      - "MMXU1.Hz"    # Frequency
      - "MMXU1.PPV.phsA"  # Voltage Phase A
```

### Phase 3: GOOSE/SV サポート

- IEC 61850-9-2 Sampled Values subscriber
- GOOSE message publisher/subscriber
- マルチキャスト対応

### Phase 4: Edge Analytics

- 異常検知（FledgeのFilterプラグイン）
- データ圧縮（時系列圧縮）
- 予測保全（機械学習統合）

## リソース

- [LF Edge Fledge公式ドキュメント](https://lfedge.org/projects/fledge/)
- [Fledge GitHub](https://github.com/fledge-iot/fledge)
- [IEC 61850 Overview](https://en.wikipedia.org/wiki/IEC_61850)

## まとめ

本統合により、以下が実現されます：

✅ **プロダクショングレードのIoTゲートウェイ**（FledgePOWER）
✅ **段階的移行**（Edge Collectorとの併用）
✅ **IEC 61850対応への道筋**（将来のMMS/GOOSE実装）
✅ **データ品質管理**（Fledgeの組み込み機能）
✅ **高可用性**（ローカルバッファリング）

ハイブリッドアプローチにより、デモの即時性とプロダクション対応の両立を実現しています。
