# CRC リソース拡張ガイド

OpenShift Local (CRC) のディスクサイズとCPUコア数を拡張する手順

## 📋 現在の状態

- **ディスク**: 27.18GB / 32.68GB 使用中（83%）← **ビルド失敗の原因**
- **メモリ**: 8.2GB / 16GB 使用中
- **CPU**: デフォルト設定

## 🎯 目標設定

- **ディスク**: 50GB（拡張）
- **CPU**: 4コア（拡張）
- **メモリ**: 16GB（維持）

## ⚠️ 重要な注意事項

- **所要時間**: 約30-45分（CRC削除→設定→起動→再デプロイ）
- **データ消失**: 現在のクラスタとすべてのアプリケーションが削除されます
- **バックアップ**: 重要なデータは事前に退避してください

## 📝 手順

### ステップ1: CRC停止・削除

```bash
# 1. CRC停止
crc stop

# 2. CRC削除（確認プロンプトが表示されます）
crc delete
```

**確認プロンプト例:**
```
? Do you want to delete the CRC instance? [y/N]:
```
→ `y` を入力

### ステップ2: リソース設定

```bash
# ディスクサイズ設定（50GB）
crc config set disk-size 50

# CPUコア数設定（4コア）
crc config set cpus 4

# メモリ設定確認（16GB）
crc config view
```

**期待される出力:**
```
- consent-telemetry : yes
- cpus              : 4
- disk-size         : 50
- memory            : 16384
```

### ステップ3: CRC起動

```bash
# CRC起動（15-20分かかります）
crc start
```

**プロンプト対応:**
1. Pull secretの入力を求められた場合:
   - Red Hat アカウントで https://console.redhat.com/openshift/create/local にアクセス
   - Pull secretをコピーして貼り付け

2. 起動完了メッセージ:
```
Started the OpenShift cluster.

The server is accessible via web console at:
  https://console-openshift-console.apps-crc.testing

Log in as administrator:
  Username: kubeadmin
  Password: xxxxx-xxxxx-xxxxx-xxxxx

Log in as user:
  Username: developer
  Password: developer
```

### ステップ4: 環境設定とログイン

```bash
# CRC環境変数設定
eval $(crc oc-env)

# kubeadminパスワード確認
crc console --credentials

# kubeadminでログイン（推奨：全権限あり）
oc login -u kubeadmin https://api.crc.testing:6443
# パスワード: 上記コマンドで表示されたもの

# または、開発者ユーザーでログイン（一部権限制限あり）
# oc login -u developer https://api.crc.testing:6443
# パスワード: developer
```

**推奨**: `kubeadmin`でログインすることで、以下の操作がスムーズに実行できます：
- クラスタスコープでのPod確認
- SCC（Security Context Constraints）の付与
- すべてのnamespaceへのアクセス

### ステップ5: 完全再デプロイ

```bash
cd /Users/kkomazaw/Development/digital-twin-substations

# 一括デプロイスクリプト実行
./scripts/deploy-all-after-crc-reset.sh
```

**スクリプトの実行内容:**
1. Namespace/Project作成
2. データゾーン（Redis, InfluxDB, PostgreSQL）
3. エッジゾーン（Edge Collector, FledgePOWER）
4. OTゾーン（IEDシミュレータ）
5. アプリケーションゾーン（PowSyBl API + ビルド）
6. ITゾーン（Grafana + ダッシュボード）
7. データコンシューマー（Redis→InfluxDB）

### ステップ6: 動作確認

```bash
# 全Pod確認
oc get pods --all-namespaces | grep zone

# Route確認
oc get routes --all-namespaces

# Grafana URL取得
echo "http://$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')"

# PowSyBl API URL取得
echo "http://$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')"
```

## 🔧 トラブルシューティング

### ビルドが失敗する場合

```bash
# ビルド状態確認
oc get builds -n app-zone

# ビルドログ確認
oc logs build/powsybl-api-1 -n app-zone

# ビルド再実行
cd /Users/kkomazaw/Development/digital-twin-substations
./scripts/redeploy-powsybl-api.sh
```

### Podが起動しない場合

```bash
# Pod詳細確認
oc describe pod <pod-name> -n <namespace>

# Pod削除（自動再作成）
oc delete pod <pod-name> -n <namespace>
```

### ストレージ不足の場合

```bash
# CRC VMのストレージ使用状況確認
crc status

# 不要なイメージ削除
oc adm prune images --confirm

# 不要なビルド削除
oc delete build --all -n app-zone
```

## 📊 期待される結果

### デプロイ完了後の状態

```
NAMESPACE    NAME                                    READY   STATUS
ot-zone      ied-simulator-xxx                      1/1     Running
edge-zone    edge-collector-xxx                     1/1     Running
edge-zone    fledgepower-xxx                        1/1     Running
data-zone    redis-xxx                              1/1     Running
data-zone    influxdb-xxx                           1/1     Running
data-zone    postgres-xxx                           1/1     Running
data-zone    redis-influxdb-consumer-xxx            1/1     Running
app-zone     powsybl-api-xxx                        1/1     Running
it-zone      grafana-xxx                            1/1     Running
```

### アクセス可能なURL

- **Grafana**: http://grafana-it-zone.apps-crc.testing
  - ユーザー: admin
  - パスワード: admin

- **PowSyBl API**: http://powsybl-api-app-zone.apps-crc.testing
  - API Docs: http://powsybl-api-app-zone.apps-crc.testing/docs

## 🎯 次のステップ

1. Grafanaダッシュボードにアクセス
2. リアルタイムデータフローの確認
3. 潮流分析APIのテスト
4. セキュリティ分析の実行

## 📚 関連ドキュメント

- [PowSyBl高度分析設計書](POWSYBL_ADVANCED_ANALYSIS.md)
- [FledgePOWER統合ガイド](FLEDGEPOWER_INTEGRATION.md)
- [デモクイックリファレンス](DEMO_QUICK_REFERENCE.md)
