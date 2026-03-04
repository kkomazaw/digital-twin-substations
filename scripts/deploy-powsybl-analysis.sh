#!/bin/bash
# デジタルツイン変電所 - PowSyBl高度分析エンジン デプロイスクリプト

set -e

echo "=========================================="
echo "PowSyBl高度分析エンジン デプロイ開始"
echo "=========================================="

# CRC環境設定
source <(crc oc-env)

cd /Users/kkomazaw/Development/digital-twin-substations

# 1. PowSyBl Analysis BuildConfig/ImageStream/Deployment作成
echo ""
echo "[1/4] PowSyBl Analysis BuildConfig/ImageStream/Deployment作成中..."
echo "----------------------------------------"

oc apply -f openshift/app-zone/powsybl-analysis-deployment.yaml

echo "✓ BuildConfig/ImageStream/Deployment作成完了"

# 2. PowSyBl Analysis Engine イメージビルド
echo ""
echo "[2/4] PowSyBl Analysis Engine イメージビルド中..."
echo "----------------------------------------"

# アーカイブ作成
tar -czf /tmp/powsybl-analysis.tar.gz -C deployments/powsybl-analysis-engine .

# ビルド実行
oc start-build powsybl-analysis \
  --from-archive=/tmp/powsybl-analysis.tar.gz \
  --follow \
  --namespace=app-zone

echo "✓ PowSyBl Analysis Engine イメージビルド完了"

# Pod削除（新しいイメージを使用するため）
echo "既存Pod削除（新イメージ適用）..."
oc delete pod -l app=powsybl-analysis -n app-zone --ignore-not-found=true

# Pod起動待機
echo "PowSyBl Analysis Pod 起動待機中..."
sleep 10
oc wait --for=condition=Ready pod -l app=powsybl-analysis -n app-zone --timeout=300s

echo "✓ PowSyBl Analysis デプロイメント完了"

# 3. 分析結果ダッシュボード ConfigMap デプロイ
echo ""
echo "[3/4] 分析結果ダッシュボード ConfigMap デプロイ中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-analysis-dashboard.yaml

echo "✓ 分析結果ダッシュボード ConfigMap デプロイ完了"

# 4. Grafana デプロイメント更新
echo ""
echo "[4/4] Grafana デプロイメント更新中..."
echo "----------------------------------------"

oc apply -f openshift/it-zone/grafana-deployment.yaml

# Grafana Pod 再起動
echo "Grafana Pod 再起動中..."
oc delete pod -l app=grafana -n it-zone

# Pod 起動待機
echo "Grafana Pod 起動待機中..."
oc wait --for=condition=Ready pod -l app=grafana -n it-zone --timeout=120s

echo "✓ Grafana デプロイメント更新完了"

# 5. デプロイ状態確認
echo ""
echo "=========================================="
echo "デプロイ完了 - 状態確認"
echo "=========================================="

echo ""
echo "PowSyBl Analysis (app-zone):"
oc get pods -n app-zone -l app=powsybl-analysis

echo ""
echo "Grafana (it-zone):"
oc get pods -n it-zone -l app=grafana

echo ""
echo "Routes:"
POWSYBL_ROUTE=$(oc get route powsybl-analysis -n app-zone -o jsonpath='{.spec.host}')
GRAFANA_ROUTE=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}')

echo "  PowSyBl Analysis API: http://${POWSYBL_ROUTE}"
echo "  Grafana:              http://${GRAFANA_ROUTE}"

echo ""
echo "=========================================="
echo "✓ PowSyBl高度分析エンジン デプロイ完了"
echo "=========================================="
echo ""
echo "利用可能な分析機能:"
echo "  1. Load Flow Analysis (潮流計算)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/loadflow"
echo ""
echo "  2. Security Analysis (N-1/N-K分析)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/security"
echo ""
echo "  3. Sensitivity Analysis (感度分析)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/sensitivity"
echo ""
echo "  4. Comprehensive Analysis (包括的分析)"
echo "     POST http://${POWSYBL_ROUTE}/api/v1/comprehensive-analysis/ieee14"
echo ""
echo "API ドキュメント:"
echo "  http://${POWSYBL_ROUTE}/docs"
echo ""
echo "Grafana ダッシュボード:"
echo "  ダッシュボード名: 'PowSyBl Advanced Analysis Results'"
echo "  ログイン: admin / admin"
echo ""
