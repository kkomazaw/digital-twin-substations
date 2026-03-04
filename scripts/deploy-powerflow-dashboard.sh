#!/bin/bash
# デジタルツイン変電所 - 潮流分析ダッシュボードデプロイスクリプト

set -e

echo "=========================================="
echo "潮流分析ダッシュボード デプロイ開始"
echo "=========================================="

# CRC環境設定
source <(crc oc-env)

# 1. 潮流分析ダッシュボード ConfigMap デプロイ
echo ""
echo "[1/2] 潮流分析ダッシュボード ConfigMap デプロイ中..."
echo "----------------------------------------"

cd /Users/kkomazaw/Development/digital-twin-substations

oc apply -f openshift/it-zone/grafana-powerflow-dashboard.yaml

echo "✓ 潮流分析ダッシュボード ConfigMap デプロイ完了"

# 2. Grafana デプロイメント更新
echo ""
echo "[2/2] Grafana デプロイメント更新中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-deployment.yaml

# Grafana Pod 再起動
echo "Grafana Pod 再起動中..."
oc delete pod -l app=grafana -n it-zone

# Pod 起動待機
echo "Grafana Pod 起動待機中..."
oc wait --for=condition=Ready pod -l app=grafana -n it-zone --timeout=120s

echo "✓ Grafana デプロイメント更新完了"

# 3. デプロイ状態確認
echo ""
echo "=========================================="
echo "デプロイ完了 - 状態確認"
echo "=========================================="

echo ""
echo "Grafana (it-zone):"
oc get pods -n it-zone -l app=grafana

echo ""
echo "Grafana Route:"
GRAFANA_ROUTE=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')
echo $GRAFANA_ROUTE

echo ""
echo "=========================================="
echo "✓ 潮流分析ダッシュボード デプロイ完了"
echo "=========================================="
echo ""
echo "Grafana ダッシュボードにアクセスして"
echo "「Power Flow Analysis (PowSyBl)」を確認してください。"
echo ""
echo "Grafana URL: http://${GRAFANA_ROUTE}"
echo "ログイン情報: admin / admin"
echo ""
echo "ダッシュボードの特徴:"
echo "  - 電圧プロファイル（3相）"
echo "  - 電流分布（3相）"
echo "  - 有効電力フロー"
echo "  - 無効電力フロー"
echo "  - 系統周波数"
echo "  - 力率"
echo "  - 皮相電力（計算値）"
echo "  - アラーム状態"
echo ""
