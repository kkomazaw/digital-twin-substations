アプラ# デジタルツイン変電所デモ 操作手順書

## 目次
1. [デモ概要](#デモ概要)
2. [アーキテクチャ説明](#アーキテクチャ説明)
3. [事前準備](#事前準備)
4. [デプロイ手順](#デプロイ手順)
5. [デモシナリオ](#デモシナリオ)
6. [トラブルシューティング](#トラブルシューティング)

---

## デモ概要

このデモは、変電所のデジタルツインをOpenShift Local上で実現するものです。
IEC 62443セキュリティ標準に準拠した5層のゾーン分離アーキテクチャを実装しています。

### デモで実現できること

1. **リアルタイムテレメトリ収集**: 複数のIED（Intelligent Electronic Device）から電気測定データをリアルタイムで収集
2. **ゾーンベースのセキュリティ**: OT/Edge/Data/Application/ITの5層セキュリティゾーン
3. **データストリーミング**: Redisストリームによるスケーラブルなデータパイプライン
4. **時系列データ管理**: InfluxDBによる高速な時系列データ保存・クエリ
5. **リアルタイム可視化**: Grafanaによるダッシュボード表示
6. **REST API**: PowSyBlベースの電力系統解析API

---

## アーキテクチャ説明

### 5層セキュリティゾーン構成

```
┌─────────────────────────────────────────────────────────────┐
│ IT Zone (IEC 62443 Level 5)                                 │
│ - Grafana: 可視化ダッシュボード                              │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ Application Zone (IEC 62443 Level 4)                        │
│ - PowSyBl API: 電力系統解析・監視API                         │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ Data Zone (IEC 62443 Data Layer)                            │
│ - Redis: メッセージストリーム                                 │
│ - InfluxDB: 時系列データベース                                │
│ - PostgreSQL: メタデータストレージ                            │
│ - Redis-InfluxDB Consumer: データ永続化サービス               │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ Edge Zone (IEC 62443 Level 3 - DMZ)                         │
│ - Edge Collector: データ集約・前処理                         │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ OT Zone (IEC 62443 Level 0-2)                               │
│ - IED Simulator (×3): 電気測定デバイスシミュレータ            │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

```
IED Simulator → Edge Collector → Redis Stream → InfluxDB Consumer → InfluxDB
                                                                         ↓
                                                                    Grafana
                                                                    PowSyBl API
```

---

## 事前準備

### 必要な環境

- **OS**: macOS (Apple Silicon推奨)
- **メモリ**: 16GB以上
- **ディスク**: 40GB以上の空き容量
- **ソフトウェア**:
  - OpenShift Local (CRC) 2.58以上
  - Red Hat Pull Secret

### OpenShift Localのセットアップ

```bash
# CRCのインストール確認
crc version

# CRCのセットアップ
crc setup

# CRC起動（初回は5-10分かかります）
crc start

# 環境変数の設定
eval $(crc oc-env)

# kubeadminでログイン（パスワードは crc console --credentials で確認）
oc login -u kubeadmin https://api.crc.testing:6443
```

---

## デプロイ手順

### 1. 完全自動デプロイ（推奨）

```bash
# プロジェクトディレクトリに移動
cd /path/to/digital-twin-substations

# 一括デプロイスクリプトを実行
./scripts/redeploy-all.sh
```

このスクリプトは以下を自動実行します：
- プロジェクト/名前空間の作成
- コンテナイメージのビルド（約5-10分）
- 権限設定
- 全コンポーネントのデプロイ

### 2. 権限修正（kubeadmin権限が必要）

```bash
# anyuid SCCを全サービスアカウントに付与
oc adm policy add-scc-to-user anyuid -z default -n ot-zone
oc adm policy add-scc-to-user anyuid -z default -n edge-zone
oc adm policy add-scc-to-user anyuid -z default -n data-zone
oc adm policy add-scc-to-user anyuid -z default -n app-zone

# デプロイメントを再起動
oc rollout restart deployment -n ot-zone ied-simulator
oc rollout restart deployment -n edge-zone edge-collector
oc rollout restart deployment -n data-zone influxdb postgres redis-influxdb-consumer
oc rollout restart deployment -n app-zone powsybl-api
```

### 3. デプロイ状態の確認

```bash
# 全Podの状態確認
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"

# 期待される状態
# ot-zone:    ied-simulator (3/3 Running)
# edge-zone:  edge-collector (1/1 Running)
# data-zone:  redis (1/1 Running), influxdb (1/1 Running),
#             postgres (1/1 Running), redis-influxdb-consumer (1/1 Running)
# app-zone:   powsybl-api (2/2 Running)
# it-zone:    grafana (1/1 Running)
```

### 4. アクセスURLの取得

```bash
# GrafanaとAPIのURL確認
oc get routes -n it-zone
oc get routes -n app-zone

# 出力例：
# grafana-it-zone.apps-crc.testing
# powsybl-api-app-zone.apps-crc.testing
```

---

## デモシナリオ

### シナリオ1: データフロー全体の確認

#### 1-1. IEDシミュレータの動作確認

```bash
# IEDシミュレータのログを確認（リアルタイム）
oc logs -n ot-zone -l app=ied-simulator -f --tail=20

# 確認ポイント：
# - 3相電圧/電流値が1秒ごとに生成されている
# - edge-collector へ送信している
# - station-a の測定データ
```

**期待される出力例：**
```
[2026-03-03 01:30:45] IED ied-simulator-xxx: Sending data to edge-collector:8888
  Station: station-a
  Voltage A: 66234.5V, Current A: 145.2A
  Voltage B: 66189.3V, Current B: 144.8A
  Voltage C: 66245.1V, Current C: 145.3A
  Frequency: 50.02Hz
```

#### 1-2. Edge Collectorの動作確認

```bash
# Edge Collectorのログを確認
oc logs -n edge-zone -l app=edge-collector -f --tail=20

# 確認ポイント：
# - IEDから受信したデータを処理
# - 異常検知ロジックの動作
# - Redisストリームへの送信
```

**期待される出力例：**
```
[2026-03-03 01:30:45] Received data from 10.128.x.x
[2026-03-03 01:30:45] Station: station-a, IED: ied-simulator-xxx
[2026-03-03 01:30:45] Anomaly detected: False
[2026-03-03 01:30:45] Sent to Redis stream 'substation-telemetry'
```

#### 1-3. Redisストリームの確認

```bash
# Redis Podに接続
POD=$(oc get pod -n data-zone -l app=redis -o jsonpath='{.items[0].metadata.name}')
oc exec -n data-zone $POD -it -- redis-cli

# Redisコマンドでストリーム確認
XLEN substation-telemetry
# 出力: ストリーム内のメッセージ数

XRANGE substation-telemetry - + COUNT 5
# 出力: 最新5件のメッセージ内容

# 終了
exit
```

#### 1-4. InfluxDB Consumerの動作確認

```bash
# Consumerのログを確認
oc logs -n data-zone -l app=redis-influxdb-consumer -f --tail=20

# 確認ポイント：
# - Redisストリームからのデータ読み取り
# - InfluxDBへの書き込み成功
# - 処理済みメッセージのACK
```

**期待される出力例：**
```
[2026-03-03 01:30:46] Consumer group 'influxdb-consumers' member 'redis-influxdb-consumer-xxx'
[2026-03-03 01:30:46] Read 10 messages from stream
[2026-03-03 01:30:46] Written 10 measurements to InfluxDB bucket 'telemetry'
[2026-03-03 01:30:46] Acknowledged messages
```

#### 1-5. InfluxDBデータの確認

```bash
# InfluxDB Podに接続
POD=$(oc get pod -n data-zone -l app=influxdb -o jsonpath='{.items[0].metadata.name}')
oc exec -n data-zone $POD -it -- influx

# InfluxDB CLIでクエリ
> auth
Token: my-super-secret-auth-token

> use telemetry
> SELECT COUNT(*) FROM measurements
# 出力: 保存されているデータポイント数

> SELECT * FROM measurements ORDER BY time DESC LIMIT 10
# 出力: 最新10件の測定データ

> exit
```

---

### シナリオ2: Grafanaダッシュボードでの可視化

#### 2-1. Grafanaへのアクセス

```bash
# GrafanaのURLを取得
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')
echo "Grafana URL: http://${GRAFANA_URL}"

# ブラウザでアクセス
# ユーザー名: admin
# パスワード: admin
```

#### 2-2. ダッシュボードの確認

1. ログイン後、左メニューから「Dashboards」を選択
2. 「Substation Monitoring Dashboard」を開く

**ダッシュボードの見方：**

- **上段パネル**: リアルタイム電圧・電流値
  - 3相（A/B/C）の電圧波形をグラフ表示
  - 各IEDからのデータを色分け表示

- **中段パネル**: 周波数モニタリング
  - 系統周波数の推移（50Hz基準）
  - 周波数偏差の検出

- **下段パネル**: 異常検知アラート
  - 異常検知されたイベントのリスト
  - タイムスタンプと詳細情報

#### 2-3. データ更新の確認

1. ダッシュボード右上の更新間隔を「5s」に設定
2. リアルタイムでグラフが更新されることを確認
3. 時間範囲を「Last 5 minutes」に設定して最新データを表示

---

### シナリオ3: PowSyBl APIの利用

#### 3-1. APIエンドポイントの確認

```bash
# API URLを取得
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')
echo "API URL: http://${API_URL}"

# APIドキュメント（Swagger UI）にアクセス
echo "API Docs: http://${API_URL}/docs"
```

#### 3-2. APIの動作確認

**1. ヘルスチェック**
```bash
curl http://${API_URL}/health
# 期待される出力: {"status":"healthy"}
```

**2. 変電所一覧の取得**
```bash
curl http://${API_URL}/stations
# 期待される出力: station-aの情報
```

**3. リアルタイムメトリクスの取得**
```bash
curl "http://${API_URL}/stations/station-a/metrics?duration=5m"
# 期待される出力: 過去5分間の測定データ（JSON形式）
```

**出力例：**
```json
{
  "station_id": "station-a",
  "time_range": "5m",
  "metrics": {
    "voltage_a": {
      "mean": 66234.5,
      "min": 66180.2,
      "max": 66289.7,
      "current": 66245.3
    },
    "current_a": {
      "mean": 145.2,
      "min": 144.8,
      "max": 145.6,
      "current": 145.3
    },
    "frequency": {
      "mean": 50.01,
      "min": 49.98,
      "max": 50.04,
      "current": 50.02
    }
  },
  "data_points": 300
}
```

**4. 異常検知イベントの取得**
```bash
curl "http://${API_URL}/stations/station-a/anomalies?limit=10"
# 期待される出力: 最新10件の異常検知イベント
```

---

### シナリオ4: ネットワークポリシーの確認

#### 4-1. ゾーン間通信の制限確認

```bash
# OT ZoneからIT Zoneへの直接アクセスが拒否されることを確認
POD=$(oc get pod -n ot-zone -l app=ied-simulator -o jsonpath='{.items[0].metadata.name}')
oc exec -n ot-zone $POD -- curl -m 5 grafana.it-zone.svc.cluster.local:3000
# 期待される結果: タイムアウト（通信が拒否される）
```

#### 4-2. 許可された通信経路の確認

```bash
# OT Zone → Edge Zone（許可）
POD=$(oc get pod -n ot-zone -l app=ied-simulator -o jsonpath='{.items[0].metadata.name}')
oc exec -n ot-zone $POD -- curl -m 5 edge-collector.edge-zone.svc.cluster.local:8888
# 期待される結果: 接続成功

# Edge Zone → Data Zone（許可）
POD=$(oc get pod -n edge-zone -l app=edge-collector -o jsonpath='{.items[0].metadata.name}')
oc exec -n edge-zone $POD -- nc -zv redis.data-zone.svc.cluster.local 6379
# 期待される結果: Connection succeeded
```

---

### シナリオ5: スケーリングとレジリエンス

#### 5-1. IEDシミュレータのスケールアウト

```bash
# IEDシミュレータを5台に増加
oc scale deployment ied-simulator -n ot-zone --replicas=5

# スケール後の確認
oc get pods -n ot-zone -w
# 5つのPodが起動することを確認

# データ量の増加を確認（Grafanaまたはログで）
oc logs -n edge-zone -l app=edge-collector -f
# より多くのIEDからデータを受信していることを確認
```

#### 5-2. Edge Collectorの冗長化

```bash
# Edge Collectorを2台に増加
oc scale deployment edge-collector -n edge-zone --replicas=2

# 負荷分散の確認
oc get pods -n edge-zone -w

# IEDシミュレータが2台のCollectorに分散接続することを確認
oc logs -n ot-zone -l app=ied-simulator | grep "Connected to"
```

#### 5-3. Podの自動復旧確認

```bash
# 意図的にPodを削除
POD=$(oc get pod -n data-zone -l app=redis -o jsonpath='{.items[0].metadata.name}')
oc delete pod $POD -n data-zone

# 自動的に新しいPodが起動することを確認
oc get pods -n data-zone -w
# RedisのPodが自動的に再作成される

# データ損失がないことを確認（Redisは揮発性だが、InfluxDBにデータが保存されている）
oc logs -n data-zone -l app=redis-influxdb-consumer
# Consumerが再接続してデータ処理を継続
```

---

## トラブルシューティング

### 問題1: Podが起動しない（CrashLoopBackOff）

**症状:**
```bash
oc get pods -n ot-zone
# NAME                             READY   STATUS             RESTARTS
# ied-simulator-xxx                0/1     CrashLoopBackOff   5
```

**原因と対策:**

1. **権限エラー（Permission Denied）**
```bash
# ログを確認
oc logs -n ot-zone <pod-name>
# "Permission denied" が表示される場合

# 解決策: anyuid SCCを付与（kubeadmin権限が必要）
oc login -u kubeadmin
oc adm policy add-scc-to-user anyuid -z default -n ot-zone
oc rollout restart deployment ied-simulator -n ot-zone
```

2. **ディスク容量不足**
```bash
# ノードの状態を確認
oc get nodes
# DiskPressureがTrueの場合

# 解決策: ディスクをクリーンアップ
crc cleanup
# または不要なイメージを削除
oc adm prune images --confirm
```

### 問題2: Podが"Pending"状態のまま

**症状:**
```bash
oc get pods -n data-zone
# NAME          READY   STATUS    RESTARTS
# influxdb-xxx  0/1     Pending   0
```

**原因と対策:**

```bash
# Podの詳細を確認
oc describe pod <pod-name> -n data-zone

# Taints（汚染）が原因の場合
Events:
  Warning  FailedScheduling  ... 0/1 nodes available: 1 node(s) had taint(s)

# 解決策: Taintを削除
./scripts/fix-node-taints.sh

# またはデプロイメントに toleration が設定されているか確認
oc get deployment influxdb -n data-zone -o yaml | grep -A 5 tolerations
```

### 問題3: データがGrafanaに表示されない

**症状:** Grafanaダッシュボードにデータが表示されない

**診断手順:**

```bash
# 1. IEDシミュレータが動作しているか
oc logs -n ot-zone -l app=ied-simulator --tail=10
# データ送信ログがあることを確認

# 2. Edge Collectorがデータを受信しているか
oc logs -n edge-zone -l app=edge-collector --tail=10
# "Received data" ログがあることを確認

# 3. Redisにデータが流れているか
POD=$(oc get pod -n data-zone -l app=redis -o jsonpath='{.items[0].metadata.name}')
oc exec -n data-zone $POD -- redis-cli XLEN substation-telemetry
# 0より大きい値が返ることを確認

# 4. InfluxDB Consumerが動作しているか
oc logs -n data-zone -l app=redis-influxdb-consumer --tail=10
# "Written to InfluxDB" ログがあることを確認

# 5. InfluxDBに接続できるか（Grafanaから）
POD=$(oc get pod -n it-zone -l app=grafana -o jsonpath='{.items[0].metadata.name}')
oc logs -n it-zone $POD | grep influxdb
# 接続エラーがないことを確認
```

### 問題4: OpenShift Local (CRC)が起動しない

**症状:**
```bash
crc start
# Error: ...
```

**対策:**

```bash
# 1. CRCの状態確認
crc status

# 2. CRCの削除と再作成（最終手段）
crc delete
crc setup
crc start

# 3. ログの確認
tail -f ~/.crc/crc.log
```

### 問題5: メモリ不足

**症状:** Podが頻繁に再起動、OOMKilled

```bash
# Podのリソース使用状況確認
oc adm top pods --all-namespaces

# CRCのメモリ使用状況確認
crc status
# RAM Usage: X GB of Y GB

# 対策: レプリカ数を減らす
oc scale deployment ied-simulator -n ot-zone --replicas=1
oc scale deployment powsybl-api -n app-zone --replicas=1
```

---

## 便利なコマンド集

### ログ確認

```bash
# 特定Podのログをリアルタイム表示
oc logs -n <namespace> <pod-name> -f

# ラベルセレクタでログ表示
oc logs -n ot-zone -l app=ied-simulator -f

# 過去のログ表示（クラッシュしたPod）
oc logs -n data-zone <pod-name> --previous

# 全ゾーンのPod状態を一覧表示
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
  echo "=== $zone ==="
  oc get pods -n $zone
done
```

### リソース監視

```bash
# リソース使用状況
oc adm top nodes
oc adm top pods -n data-zone

# イベント確認
oc get events -n data-zone --sort-by='.lastTimestamp'

# デプロイメント状態
oc get deployments --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"
```

### デバッグ

```bash
# Podに直接接続
oc exec -n data-zone <pod-name> -it -- /bin/sh

# サービスの疎通確認
oc exec -n edge-zone <pod-name> -- curl -v redis.data-zone.svc.cluster.local:6379

# ネットワークポリシー確認
oc get networkpolicies -n ot-zone
oc describe networkpolicy allow-to-edge -n ot-zone
```

---

## デモの片付け

```bash
# 全プロジェクトを削除
oc delete project digital-twin ot-zone edge-zone data-zone app-zone it-zone

# CRCを停止
crc stop

# CRCを完全に削除（必要な場合のみ）
crc delete
```

---

## 付録: カスタマイズ例

### IEDシミュレータのパラメータ調整

デプロイメントマニフェストを編集：
```yaml
# openshift/ot-zone/ied-deployment.yaml
env:
- name: DATA_INTERVAL
  value: "0.5"  # データ送信間隔を0.5秒に変更
- name: BASE_VOLTAGE
  value: "154000"  # 基準電圧を154kVに変更
```

```bash
# 変更を適用
oc apply -f openshift/ot-zone/ied-deployment.yaml
```

### Grafanaダッシュボードのカスタマイズ

1. Grafana UIでダッシュボードを編集
2. JSON形式でエクスポート
3. ConfigMapとして保存：

```bash
# 新しいダッシュボードをConfigMapに追加
oc create configmap custom-dashboard --from-file=dashboard.json -n it-zone
```

---

## サポート情報

- **GitHub Issues**: https://github.com/anthropics/claude-code/issues
- **OpenShift Local ドキュメント**: https://developers.redhat.com/products/openshift-local
- **IEC 62443 標準**: https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards

---

**デモ手順書 バージョン 1.0**
最終更新: 2026-03-03
