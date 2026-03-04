#!/bin/bash
# デジタルツイン変電所 - トポロジーダッシュボードデプロイスクリプト

set -e

echo "=========================================="
echo "トポロジーダッシュボード デプロイ開始"
echo "=========================================="

# CRC環境設定
source <(crc oc-env)

# 1. PowSyBl API イメージ再ビルド
echo ""
echo "[1/4] PowSyBl API イメージ再ビルド中..."
echo "----------------------------------------"

cd /Users/kkomazaw/Development/digital-twin-substations

# アーカイブ作成
tar -czf /tmp/powsybl-api.tar.gz -C deployments/powsybl-api .

# ビルド実行
oc start-build powsybl-api \
  --from-archive=/tmp/powsybl-api.tar.gz \
  --follow \
  --namespace=app-zone

echo "✓ PowSyBl API イメージビルド完了"

# 2. トポロジーダッシュボード ConfigMap デプロイ
echo ""
echo "[2/4] トポロジーダッシュボード ConfigMap デプロイ中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-topology-dashboard.yaml

echo "✓ トポロジーダッシュボード ConfigMap デプロイ完了"

# 3. Grafana デプロイメント更新
echo ""
echo "[3/4] Grafana デプロイメント更新中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-deployment.yaml

# Grafana Pod 再起動
echo "Grafana Pod 再起動中..."
oc delete pod -l app=grafana -n it-zone

# Pod 起動待機
echo "Grafana Pod 起動待機中..."
oc wait --for=condition=Ready pod -l app=grafana -n it-zone --timeout=120s

echo "✓ Grafana デプロイメント更新完了"

# 4. PowSyBl API デプロイメント更新
echo ""
echo "[4/4] PowSyBl API デプロイメント更新中..."
echo "----------------------------------------"

# PowSyBl API Pod 再起動（新しいイメージ使用）
oc delete pod -l app=powsybl-api -n app-zone

# Pod 起動待機
echo "PowSyBl API Pod 起動待機中..."
oc wait --for=condition=Ready pod -l app=powsybl-api -n app-zone --timeout=120s

echo "✓ PowSyBl API デプロイメント更新完了"

# 5. デプロイ状態確認
echo ""
echo "=========================================="
echo "デプロイ完了 - 状態確認"
echo "=========================================="

echo ""
echo "Grafana (it-zone):"
oc get pods -n it-zone -l app=grafana

echo ""
echo "PowSyBl API (app-zone):"
oc get pods -n app-zone -l app=powsybl-api

echo ""
echo "Grafana Route:"
oc get route grafana -n it-zone -o jsonpath='{.spec.host}'
echo ""

echo ""
echo "=========================================="
echo "✓ トポロジーダッシュボード デプロイ完了"
echo "=========================================="
echo ""
echo "Grafana ダッシュボードにアクセスして"
echo "「Substation Data Flow Topology」を確認してください。"
echo ""
echo "PowSyBl API トポロジーエンドポイント:"
echo "  http://$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')/topology"
echo ""
