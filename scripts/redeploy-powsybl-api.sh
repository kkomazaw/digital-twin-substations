#!/bin/bash
# デジタルツイン変電所 - PowSyBl API 再デプロイスクリプト（分析機能追加版）

set -e

echo "=========================================="
echo "PowSyBl API 再デプロイ開始（分析機能追加）"
echo "=========================================="

# CRC環境設定
source <(crc oc-env)

cd /Users/kkomazaw/Development/digital-twin-substations

# 1. 古いビルドをクリーンアップ
echo ""
echo "[1/5] 古いビルドのクリーンアップ中..."
echo "----------------------------------------"

oc delete build --all -n app-zone
oc delete pod --field-selector=status.phase==Failed -n app-zone --ignore-not-found=true
oc delete pod --field-selector=status.phase==Succeeded -n app-zone --ignore-not-found=true

echo "✓ クリーンアップ完了"

# 2. PowSyBl API イメージ再ビルド
echo ""
echo "[2/5] PowSyBl API イメージ再ビルド中..."
echo "----------------------------------------"

# アーカイブ作成
tar -czf /tmp/powsybl-api.tar.gz -C deployments/powsybl-api .

# ビルド実行
oc start-build powsybl-api \
  --from-archive=/tmp/powsybl-api.tar.gz \
  --follow \
  --namespace=app-zone

echo "✓ PowSyBl API イメージビルド完了"

# 3. PowSyBl API デプロイメント更新
echo ""
echo "[3/5] PowSyBl API デプロイメント更新中..."
echo "----------------------------------------"

# PowSyBl API Pod 再起動（新しいイメージ使用）
oc delete pod -l app=powsybl-api -n app-zone

# Pod 起動待機
echo "PowSyBl API Pod 起動待機中..."
sleep 10
oc wait --for=condition=Ready pod -l app=powsybl-api -n app-zone --timeout=180s

echo "✓ PowSyBl API デプロイメント更新完了"

# 4. 分析結果ダッシュボード更新
echo ""
echo "[4/5] 分析結果ダッシュボード更新中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-analysis-dashboard.yaml

echo "✓ 分析結果ダッシュボード更新完了"

# 5. Grafana デプロイメント更新
echo ""
echo "[5/5] Grafana デプロイメント更新中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-deployment.yaml

# Grafana Pod 再起動
echo "Grafana Pod 再起動中..."
oc delete pod -l app=grafana -n it-zone

# Pod 起動待機
echo "Grafana Pod 起動待機中..."
oc wait --for=condition=Ready pod -l app=grafana -n it-zone --timeout=120s

echo "✓ Grafana デプロイメント更新完了"

# デプロイ状態確認
echo ""
echo "=========================================="
echo "デプロイ完了 - 状態確認"
echo "=========================================="

echo ""
echo "PowSyBl API (app-zone):"
oc get pods -n app-zone -l app=powsybl-api

echo ""
echo "Grafana (it-zone):"
oc get pods -n it-zone -l app=grafana

echo ""
echo "Routes:"
POWSYBL_ROUTE=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}')
GRAFANA_ROUTE=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')

echo "  PowSyBl API:  http://${POWSYBL_ROUTE}"
echo "  Grafana:      http://${GRAFANA_ROUTE}"

echo ""
echo "=========================================="
echo "✓ PowSyBl API 再デプロイ完了"
echo "=========================================="
echo ""
echo "新しく追加された分析機能:"
echo ""
echo "  1. Load Flow Analysis (潮流計算)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/loadflow"
echo "     Example:"
echo "       curl -X POST http://${POWSYBL_ROUTE}/api/v1/loadflow \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"network_id\":\"ieee14\"}'"
echo ""
echo "  2. Security Analysis (N-1分析)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/security"
echo "     Example:"
echo "       curl -X POST http://${POWSYBL_ROUTE}/api/v1/security \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"network_id\":\"ieee14\",\"contingencies\":[]}'"
echo ""
echo "  3. Sensitivity Analysis (感度分析)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/sensitivity"
echo "     Example:"
echo "       curl -X POST http://${POWSYBL_ROUTE}/api/v1/sensitivity \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"network_id\":\"ieee14\",\"factors\":[],\"analysis_type\":\"DC\"}'"
echo ""
echo "  4. Networks List"
echo "     GET http://${POWSYBL_ROUTE}/api/v1/networks"
echo ""
echo "API ドキュメント:"
echo "  http://${POWSYBL_ROUTE}/docs"
echo ""
echo "Grafana ダッシュボード:"
echo "  ダッシュボード名: 'PowSyBl Advanced Analysis Results'"
echo "  URL: http://${GRAFANA_ROUTE}"
echo "  ログイン: admin / admin"
echo ""
