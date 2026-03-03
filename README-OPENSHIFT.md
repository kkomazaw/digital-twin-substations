# デジタルツイン変電所デモ - OpenShift Local版

変電所のデジタルツインをオープンソースで実現するデモプロジェクトです。
IEC 62443準拠のゾーン分離を実装し、OpenShift Local上で動作します。

## 📖 ドキュメント

- **[デモ操作手順書](docs/DEMO_GUIDE.md)** - 包括的なデモガイド（5つのシナリオ、トラブルシューティング含む）
- **[クイックリファレンス](docs/DEMO_QUICK_REFERENCE.md)** - デモ実施時の即座参照用チートシート
- **[ネットワーク設計書](docs/NETWORK_DESIGN.md)** - アーキテクチャとセキュリティゾーンの詳細

## アーキテクチャ

このデモは、NETWORK_DESIGN.mdに基づいて以下のゾーンで構成されています:

```
┌─────────────────────────────────────────────────────────┐
│                    IT Zone                              │
│  - Grafana (可視化) ← Route経由で外部公開               │
│  - API Gateway (将来実装)                                │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              Application Zone                           │
│  - PowSyBl API (電力系統解析) ← Route経由で公開         │
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

## OpenShift Localの特徴

- **Route**: KubernetesのNodePortやLoadBalancerの代わりにOpenShift Routeを使用
- **内部イメージレジストリ**: コンテナイメージをOpenShift内部レジストリに保存
- **プロジェクト**: Kubernetesのnamespaceの代わりにOpenShiftのprojectを使用
- **oc CLI**: kubectlの代わりにocコマンドを使用

## 必要な環境

- **OpenShift Local (CRC)**: バージョン 2.0以降
- **Podman**: コンテナイメージのビルド用
- **oc CLI**: OpenShiftコマンドラインツール
- **Bash**: デプロイスクリプト実行用

## OpenShift Localのセットアップ

### 1. OpenShift Localのインストール

公式サイトからダウンロード: https://developers.redhat.com/products/openshift-local/overview

```bash
# CRCのセットアップ
crc setup

# メモリとCPUを設定（推奨）
crc config set memory 16384
crc config set cpus 4

# OpenShift Localを起動
crc start

# 環境変数を設定
eval $(crc oc-env)

# developer ユーザーでログイン
oc login -u developer https://api.crc.testing:6443
```

### 2. イメージビルドとプッシュ

```bash
./scripts/build-images-openshift.sh
```

このスクリプトは以下を実行します:
1. Podmanでコンテナイメージをビルド
2. OpenShift内部レジストリにログイン
3. イメージをレジストリにプッシュ

### 3. デプロイ

```bash
./scripts/deploy-openshift.sh
```

このスクリプトは以下を実行します:
1. 各ゾーンのプロジェクト（名前空間）作成
2. Data Zoneコンポーネントのデプロイ（Kafka, InfluxDB, Postgres）
3. Edge Zone、OT Zone、Application Zone、IT Zoneのデプロイ
4. NetworkPolicyの適用
5. Routeの作成（Grafana、PowSyBl API）

### 4. 動作確認

```bash
./scripts/test-deployment-openshift.sh
```

または手動で確認:

```bash
# 全Podの確認
oc get pods --all-namespaces

# Routeの確認
oc get routes -n it-zone
oc get routes -n app-zone

# Grafana URLを取得
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')
echo "Grafana: http://${GRAFANA_URL}"

# PowSyBl API URLを取得
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')
echo "API: http://${API_URL}"
```

### 5. アプリケーションへのアクセス

#### Grafana UI

```bash
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')
open http://${GRAFANA_URL}
```

- User: `admin`
- Password: `admin`

#### PowSyBl API

```bash
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')

# 変電所リスト取得
curl http://${API_URL}/stations

# メトリクス取得
curl http://${API_URL}/stations/station-a/metrics

# 異常検知
curl http://${API_URL}/stations/station-a/anomalies
```

### 6. クリーンアップ

```bash
./scripts/cleanup-openshift.sh
```

OpenShift Local自体を停止する場合:

```bash
crc stop
```

## データの確認

### InfluxDBに直接アクセス

```bash
oc port-forward -n data-zone svc/influxdb 8086:8086
```

ブラウザで http://localhost:8086 にアクセス
- Organization: substation
- Bucket: telemetry
- Token: my-super-secret-auth-token

### Kafkaトピックの確認

```bash
# Kafkaコンテナに入る
oc exec -it -n data-zone deployment/kafka -- bash

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
├── deployments/               # アプリケーションソース
│   ├── ied-simulator/         # IEDシミュレーター
│   ├── edge-collector/        # エッジコレクター
│   ├── kafka-influxdb-consumer/  # Kafkaコンシューマー
│   └── powsybl-api/           # 電力解析API
├── openshift/                 # OpenShift用マニフェスト
│   ├── ot-zone/               # OTゾーン
│   ├── edge-zone/             # エッジゾーン
│   ├── data-zone/             # データゾーン
│   ├── app-zone/              # アプリケーションゾーン
│   └── it-zone/               # ITゾーン
├── k8s/                       # 汎用Kubernetesマニフェスト
│   └── network-policies/      # ネットワークポリシー
└── scripts/                   # デプロイスクリプト
    ├── build-images-openshift.sh   # イメージビルド
    ├── deploy-openshift.sh         # デプロイ
    ├── cleanup-openshift.sh        # クリーンアップ
    └── test-deployment-openshift.sh # テスト
```

## OpenShift特有の機能

### Route vs Ingress

OpenShiftではIngressの代わりにRouteを使用します:

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: grafana
  namespace: it-zone
spec:
  to:
    kind: Service
    name: grafana
  port:
    targetPort: http
```

### 内部イメージレジストリ

イメージパスの形式:
```
image-registry.openshift-image-registry.svc:5000/<project>/<image>:latest
```

外部からのアクセス（ビルド・プッシュ時）:
```
default-route-openshift-image-registry.apps-crc.testing/<project>/<image>:latest
```

### Security Context Constraints (SCC)

必要に応じて権限を調整:

```bash
# anyuid SCCを付与（rootユーザーが必要な場合）
oc adm policy add-scc-to-user anyuid -z default -n <namespace>
```

## トラブルシューティング

### Podが起動しない

```bash
# Pod状態確認
oc get pods -n <namespace>

# ログ確認
oc logs -n <namespace> <pod-name>

# イベント確認
oc describe pod -n <namespace> <pod-name>
```

### イメージがプルできない

```bash
# ImageStreamの確認
oc get is -n digital-twin

# イメージを再プッシュ
./scripts/build-images-openshift.sh
```

### Routeにアクセスできない

```bash
# Routeの確認
oc get route -n <namespace>

# Serviceの確認
oc get svc -n <namespace>

# Podが稼働しているか確認
oc get pods -n <namespace>
```

### Kafkaに接続できない

Kafkaの起動を待ってから他のコンポーネントをデプロイ:

```bash
oc wait --for=condition=ready pod -l app=kafka -n data-zone --timeout=300s
```

### NetworkPolicyのデバッグ

一時的に無効化:

```bash
oc delete networkpolicies --all --all-namespaces
```

## OpenShift Console

OpenShift Localには強力なWebコンソールが付属しています:

```bash
crc console
```

デフォルトユーザー:
- **Developer**: developer / developer
- **Admin**: kubeadmin / (crc start時に表示されたパスワード)

## リソース要件

OpenShift Local推奨スペック:
- **メモリ**: 16GB以上
- **CPU**: 4コア以上
- **ディスク**: 35GB以上の空き容量

本デモの全コンポーネント起動時:
- **メモリ使用量**: 約4-6GB
- **CPU使用量**: 約2-3コア

## Kind版との違い

| 項目 | Kind版 | OpenShift Local版 |
|------|--------|-------------------|
| コンテナランタイム | Podman | CRI-O |
| ノード数 | 5 (マルチノード) | 1 (シングルノード) |
| 外部公開 | NodePort | Route |
| イメージ管理 | ローカルロード | 内部レジストリ |
| CLI | kubectl | oc |
| Web UI | なし | OpenShift Console |
| ノードセレクター | 使用 | 不使用 |

## 拡張アイデア

- [ ] TLS/HTTPSの有効化（RouteでTLS Terminationを設定）
- [ ] OAuth/OIDCによる認証（OpenShift OAuth統合）
- [ ] PersistentVolumeClaimによる永続化
- [ ] HorizontalPodAutoscaler（HPA）設定
- [ ] OpenShift Pipelinesによる CI/CD
- [ ] Service Meshの導入
- [ ] OpenShift Monitoringとの統合

## 参考資料

- [OpenShift Local Documentation](https://access.redhat.com/documentation/en-us/red_hat_openshift_local)
- [OpenShift Routes](https://docs.openshift.com/container-platform/latest/networking/routes/route-configuration.html)
- IEC 62443: Industrial automation and control systems security
- IEC 61850: Power utility automation
- [docs/NETWORK_DESIGN.md](docs/NETWORK_DESIGN.md)

## ライセンス

オープンソースプロジェクト (ライセンス未定)
