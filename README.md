# デジタルツイン変電所デモ

変電所のデジタルツインをオープンソースで実現するデモプロジェクトです。
IEC 62443準拠のゾーン分離を実装し、ローカルKubernetes環境（Kind / OpenShift Local）で動作します。

**📘 実行環境の選択:**
- **Kind版**: [このREADME](#クイックスタート-kind版) を参照
- **OpenShift Local版**: [README-OPENSHIFT.md](README-OPENSHIFT.md) を参照 ⭐推奨

## アーキテクチャ

このデモは、NETWORK_DESIGN.mdに基づいて以下のゾーンで構成されています:

```
┌─────────────────────────────────────────────────────────┐
│                    IT Zone                              │
│  - Grafana (可視化)                                      │
│  - API Gateway (将来実装)                                │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              Application Zone                           │
│  - PowSyBl API (電力系統解析)                            │
│  - 異常検知サービス                                       │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                Data Zone                                │
│  - Kafka (メッセージング)                                 │
│  - InfluxDB (時系列データ)                                │
│  - Postgres (メタデータ)                                  │
└────────────────▲────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────┐
│               Edge Zone (DMZ)                           │
│  - Edge Collector (Fledge相当)                          │
│  - プロトコル変換                                         │
│  - ローカルバッファリング                                 │
└────────────────▲────────────────────────────────────────┘
                 │ IEC 61850 (シミュレート)
┌────────────────┴────────────────────────────────────────┐
│               OT Zone (Level 0-2)                       │
│  - IED Simulator (複数台)                                │
│  - Sampled Values (SV) 生成                              │
│  - Protection Relay シミュレーション                      │
└─────────────────────────────────────────────────────────┘
```

## 主な機能

### セキュリティ (IEC 62443準拠)
- **ゾーン分離**: Kubernetes NetworkPolicyによる厳格なゾーン分離
- **OT保護**: OTゾーンへの外部直接アクセス禁止
- **一方向通信**: OT → Edge → Data の単方向データフロー

### データフロー
1. **IED Simulator** が変電所の計測データ (電圧、電流、周波数など) を生成
2. **Edge Collector** がデータを収集しKafkaに転送
3. **Kafka → InfluxDB Consumer** が時系列データベースに保存
4. **PowSyBl API** がデータを分析
5. **Grafana** でリアルタイム可視化

## 必要な環境（Kind版）

- Podman
- Kind
- kubectl
- Bash

**OpenShift Local版をご利用の場合は [README-OPENSHIFT.md](README-OPENSHIFT.md) をご覧ください。**

## クイックスタート (Kind版)

### 1. イメージビルド

```bash
./scripts/build-images.sh
```

### 2. デプロイ

```bash
./scripts/deploy.sh
```

### 3. 動作確認

全Podの起動確認:
```bash
kubectl get pods --all-namespaces
```

Grafanaにアクセス:
```
URL: http://localhost:3000
User: admin
Password: admin
```

PowSyBl APIにアクセス:
```bash
kubectl port-forward -n app-zone svc/powsybl-api 8000:8000

# 変電所リスト取得
curl http://localhost:8000/stations

# メトリクス取得
curl http://localhost:8000/stations/station-a/metrics

# 異常検知
curl http://localhost:8000/stations/station-a/anomalies
```

### 4. クリーンアップ

```bash
./scripts/cleanup.sh
```

## データの確認

### InfluxDBに直接アクセス

```bash
kubectl port-forward -n data-zone svc/influxdb 8086:8086
```

ブラウザで http://localhost:8086 にアクセス
- Organization: substation
- Bucket: telemetry
- Token: my-super-secret-auth-token

### Kafkaトピックの確認

```bash
# Kafkaコンテナに入る
kubectl exec -it -n data-zone deployment/kafka -- bash

# トピック一覧
kafka-topics.sh --bootstrap-server localhost:9092 --list

# メッセージ確認
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic substation-telemetry --from-beginning --max-messages 10
```

## ディレクトリ構成

```
.
├── CLAUDE.md                  # プロジェクト指示
├── docs/
│   └── NETWORK_DESIGN.md      # ネットワーク設計
├── kind-config.yaml           # Kindクラスター設定
├── deployments/               # アプリケーションソース
│   ├── ied-simulator/         # IEDシミュレーター
│   ├── edge-collector/        # エッジコレクター
│   ├── kafka-influxdb-consumer/  # Kafkaコンシューマー
│   └── powsybl-api/           # 電力解析API
├── k8s/                       # Kubernetesマニフェスト
│   ├── ot-zone/               # OTゾーン
│   ├── edge-zone/             # エッジゾーン
│   ├── data-zone/             # データゾーン
│   ├── app-zone/              # アプリケーションゾーン
│   ├── it-zone/               # ITゾーン
│   └── network-policies/      # ネットワークポリシー
└── scripts/                   # デプロイスクリプト
    ├── build-images.sh        # イメージビルド
    ├── deploy.sh              # デプロイ
    └── cleanup.sh             # クリーンアップ
```

## トラブルシューティング

### Podが起動しない

```bash
# Pod状態確認
kubectl get pods -n <namespace>

# ログ確認
kubectl logs -n <namespace> <pod-name>

# イベント確認
kubectl describe pod -n <namespace> <pod-name>
```

### Kafkaに接続できない

Kafkaの起動を待ってから他のコンポーネントをデプロイしてください:

```bash
kubectl wait --for=condition=ready pod -l app=kafka -n data-zone --timeout=300s
```

### NetworkPolicyのデバッグ

NetworkPolicyを一時的に無効化:

```bash
kubectl delete networkpolicies --all --all-namespaces
```

## 拡張アイデア

- [ ] Keycloakによる認証・認可
- [ ] mTLS通信の実装
- [ ] 複数変電所のシミュレーション
- [ ] AI/ML異常検知の高度化
- [ ] PowSyBlの本格的な電力潮流計算
- [ ] Prometheusメトリクス収集
- [ ] Jaegerによる分散トレーシング

## ライセンス

オープンソースプロジェクト (ライセンス未定)

## 参考資料

- IEC 62443: Industrial automation and control systems security
- IEC 61850: Power utility automation
- [docs/NETWORK_DESIGN.md](docs/NETWORK_DESIGN.md)
