# デジタルツイン変電所デモ - クイックリファレンス

## 🚀 クイックスタート（5分）

```bash
# 1. OpenShift Localにログイン
eval $(crc oc-env)
oc login -u kubeadmin https://api.crc.testing:6443

# 2. 自動デプロイ実行
cd /path/to/digital-twin-substations
./scripts/redeploy-all.sh

# 3. 権限修正（重要！）
oc adm policy add-scc-to-user anyuid -z default -n ot-zone
oc adm policy add-scc-to-user anyuid -z default -n edge-zone
oc adm policy add-scc-to-user anyuid -z default -n data-zone
oc adm policy add-scc-to-user anyuid -z default -n app-zone
oc rollout restart deployment --all -n ot-zone
oc rollout restart deployment --all -n edge-zone
oc rollout restart deployment --all -n data-zone
oc rollout restart deployment --all -n app-zone

# 4. 状態確認（全て Running になるまで待つ）
watch -n 2 'oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"'
```

---

## 📊 アクセスURL

```bash
# URLを取得
GRAFANA=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')
API=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')

echo "Grafana:    http://$GRAFANA (admin/admin)"
echo "API:        http://$API"
echo "API Docs:   http://$API/docs"
```

---

## 🎯 デモシナリオ別コマンド

### シナリオ1: データフロー確認（5分）

```bash
# ① IEDシミュレータの動作確認
oc logs -n ot-zone -l app=ied-simulator -f --tail=5

# ② Edge Collectorの動作確認
oc logs -n edge-zone -l app=edge-collector -f --tail=5

# ③ Redisストリーム確認
POD=$(oc get pod -n data-zone -l app=redis -o jsonpath='{.items[0].metadata.name}')
oc exec -n data-zone $POD -- redis-cli XLEN substation-telemetry

# ④ InfluxDB Consumer確認
oc logs -n data-zone -l app=redis-influxdb-consumer -f --tail=5
```

### シナリオ2: Grafana可視化（3分）

```bash
# Grafana URL表示
echo "http://$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')"

# ブラウザでアクセス → admin/admin でログイン
# "Substation Monitoring Dashboard" を開く
```

### シナリオ3: API利用（3分）

```bash
API=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')

# ヘルスチェック
curl http://$API/health

# 変電所メトリクス取得
curl "http://$API/stations/station-a/metrics?duration=5m" | jq .

# 異常検知イベント取得
curl "http://$API/stations/station-a/anomalies?limit=5" | jq .
```

### シナリオ4: セキュリティゾーン確認（2分）

```bash
# OT → IT 直接通信（拒否されることを確認）
POD=$(oc get pod -n ot-zone -l app=ied-simulator -o jsonpath='{.items[0].metadata.name}')
oc exec -n ot-zone $POD -- timeout 3 curl grafana.it-zone.svc.cluster.local:3000
# → タイムアウト（期待通り）

# OT → Edge 通信（許可されることを確認）
oc exec -n ot-zone $POD -- timeout 3 curl edge-collector.edge-zone.svc.cluster.local:8888
# → 成功
```

### シナリオ5: スケーリング（2分）

```bash
# IED数を増やす
oc scale deployment ied-simulator -n ot-zone --replicas=5
oc get pods -n ot-zone -w

# データ増加を確認
oc logs -n edge-zone -l app=edge-collector -f
```

---

## 🔧 トラブルシューティング（即座に対応）

### Podが起動しない

```bash
# 1. 状態確認
oc get pods -n <namespace>

# 2. ログ確認
oc logs -n <namespace> <pod-name>

# 3. Permission Denied の場合
oc adm policy add-scc-to-user anyuid -z default -n <namespace>
oc rollout restart deployment -n <namespace>

# 4. Taint の場合
./scripts/fix-node-taints.sh
```

### データが表示されない

```bash
# データフローを順番に確認
oc logs -n ot-zone -l app=ied-simulator --tail=5        # ①送信
oc logs -n edge-zone -l app=edge-collector --tail=5     # ②受信
oc exec -n data-zone $(oc get pod -n data-zone -l app=redis -o name | head -1) -- redis-cli XLEN substation-telemetry  # ③蓄積
oc logs -n data-zone -l app=redis-influxdb-consumer --tail=5  # ④保存
```

### ディスク容量不足

```bash
# 不要なリソース削除
oc adm prune images --confirm --keep-younger-than=0m

# または CRC再起動
crc stop && crc start
```

---

## 📝 よく使うコマンド

### 全体状況確認

```bash
# 全Pod状態
oc get pods --all-namespaces | grep -E "zone"

# リソース使用状況
oc adm top nodes
oc adm top pods -n data-zone

# イベント確認
oc get events --all-namespaces --sort-by='.lastTimestamp' | tail -20
```

### ログ確認

```bash
# リアルタイムログ（複数Pod）
oc logs -n ot-zone -l app=ied-simulator -f --max-log-requests=10

# 過去のログ（クラッシュしたPod）
oc logs -n data-zone <pod-name> --previous

# 全ゾーンのログを一度に
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
  echo "=== $zone ==="
  oc logs -n $zone -l zone=$zone --tail=3
done
```

### デバッグ

```bash
# Pod内でコマンド実行
oc exec -n data-zone <pod-name> -it -- /bin/sh

# ネットワーク疎通確認
oc exec -n edge-zone <pod-name> -- curl -v redis.data-zone:6379

# 設定確認
oc get deployment ied-simulator -n ot-zone -o yaml
```

---

## 🎬 デモプレゼンテーション用スクリプト

### オープニング（1分）

```
「IEC 62443準拠の変電所デジタルツインをご紹介します。
5層のセキュリティゾーンで構成され、リアルタイムに
変電所の電気測定データを収集・可視化します。」
```

**実演:**
```bash
oc get pods --all-namespaces | grep -E "zone"
```

### パート1: アーキテクチャ説明（2分）

```
「OTゾーンでIEDシミュレータが3相交流の電圧・電流を測定。
Edgeゾーンでデータ集約、DataゾーンのRedisストリームで
バッファリング後、InfluxDBに永続化されます。」
```

**実演:**
```bash
# データフロー可視化
oc logs -n ot-zone -l app=ied-simulator -f --tail=2 &
sleep 3
oc logs -n edge-zone -l app=edge-collector -f --tail=2 &
sleep 3
oc logs -n data-zone -l app=redis-influxdb-consumer -f --tail=2
```

### パート2: Grafana可視化（2分）

```
「ITゾーンのGrafanaで、全IEDのデータをリアルタイムに
可視化できます。3相電圧、電流、周波数、異常検知を
ダッシュボードで監視します。」
```

**実演:**
```bash
# Grafana URLを表示しブラウザで開く
open "http://$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')"
```

### パート3: API活用（2分）

```
「PowSyBl APIを通じて、プログラマティックにデータへ
アクセスできます。REST APIで最新メトリクスや
異常検知結果を取得可能です。」
```

**実演:**
```bash
API=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')
curl "http://$API/stations/station-a/metrics?duration=1m" | jq '.metrics'
```

### パート4: セキュリティ（1分）

```
「IEC 62443に準拠したゾーン分離により、OTゾーンから
ITゾーンへの直接通信は遮断されています。
NetworkPolicyで通信経路を制御しています。」
```

**実演:**
```bash
# 拒否される通信を実演
POD=$(oc get pod -n ot-zone -l app=ied-simulator -o jsonpath='{.items[0].metadata.name}')
oc exec -n ot-zone $POD -- timeout 2 curl grafana.it-zone:3000
echo "→ タイムアウト（期待通りブロック）"
```

### クロージング（1分）

```
「このデジタルツインは、OpenShift上でコンテナ化され、
スケーラブルかつレジリエントなアーキテクチャです。
実際の変電所への展開も想定した設計となっています。」
```

**実演:**
```bash
# スケーリングのデモ
oc scale deployment ied-simulator -n ot-zone --replicas=5
oc get pods -n ot-zone
```

---

## 📋 チェックリスト

### デモ前確認

- [ ] OpenShift Local が起動している (`crc status`)
- [ ] すべてのPodが Running (`oc get pods --all-namespaces`)
- [ ] Grafana にアクセスできる
- [ ] API にアクセスできる
- [ ] データが流れている（ログ確認）

### デモ中トラブル対応

- [ ] Podがクラッシュ → `oc logs` で原因確認
- [ ] データが止まった → Redis Consumer ログ確認
- [ ] Grafanaが表示されない → InfluxDB接続確認
- [ ] ネットワークエラー → `oc get networkpolicies`

### デモ後クリーンアップ

```bash
# プロジェクト削除
oc delete project digital-twin ot-zone edge-zone data-zone app-zone it-zone

# CRC停止（必要に応じて）
crc stop
```

---

## 🎓 よくある質問

**Q: IEDシミュレータは何台まで増やせますか？**
```bash
# 最大10台程度（OpenShift Localのリソース次第）
oc scale deployment ied-simulator -n ot-zone --replicas=10
```

**Q: データ保持期間は？**
```bash
# InfluxDBのデフォルト保持期間を確認
POD=$(oc get pod -n data-zone -l app=influxdb -o name | head -1)
oc exec -n data-zone $POD -- influx bucket list
```

**Q: カスタムダッシュボードを追加するには？**
```
Grafana UI で作成後、JSON エクスポート→ ConfigMap として保存
```

---

**クイックリファレンス バージョン 1.0**
デモ実施時はこのドキュメントを手元に！
