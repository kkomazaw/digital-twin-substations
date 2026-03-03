#!/bin/bash
set -e

echo "=========================================="
echo "OpenShift Local デプロイメント動作確認"
echo "=========================================="

# 全名前空間のPod確認
echo ""
echo "[1/6] 全Podの状態を確認..."
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"

echo ""
echo "[2/6] OT Zone (IED Simulator) のログ確認..."
oc logs -n ot-zone deployment/ied-simulator --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[3/6] Edge Zone (Edge Collector) のログ確認..."
oc logs -n edge-zone deployment/edge-collector --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[4/6] Data Zone (Kafka Consumer) のログ確認..."
oc logs -n data-zone deployment/kafka-influxdb-consumer --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[5/6] Routesの確認..."
echo "Grafana Route:"
oc get route grafana -n it-zone -o jsonpath='{.spec.host}' 2>/dev/null && echo "" || echo "  未作成"

echo "PowSyBl API Route:"
oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}' 2>/dev/null && echo "" || echo "  未作成"

echo ""
echo "[6/6] サービスの確認..."
echo "IT Zone (Grafana):"
oc get svc -n it-zone grafana

echo ""
echo "Application Zone (PowSyBl API):"
oc get svc -n app-zone powsybl-api

echo ""
echo "=========================================="
echo "テスト完了!"
echo "=========================================="
echo ""
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")
echo "次のステップ:"
echo "1. Grafana UI: http://${GRAFANA_URL} (admin/admin)"
echo "2. PowSyBl API テスト: curl http://${API_URL}/stations"
echo ""
