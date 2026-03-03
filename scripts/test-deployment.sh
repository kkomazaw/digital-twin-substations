#!/bin/bash
set -e

echo "=========================================="
echo "デプロイメント動作確認テスト"
echo "=========================================="

# 全名前空間のPod確認
echo ""
echo "[1/5] 全Podの状態を確認..."
kubectl get pods --all-namespaces

echo ""
echo "[2/5] OT Zone (IED Simulator) のログ確認..."
kubectl logs -n ot-zone deployment/ied-simulator --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[3/5] Edge Zone (Edge Collector) のログ確認..."
kubectl logs -n edge-zone deployment/edge-collector --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[4/5] Data Zone (Kafka Consumer) のログ確認..."
kubectl logs -n data-zone deployment/kafka-influxdb-consumer --tail=5 || echo "  ※まだ起動していない可能性があります"

echo ""
echo "[5/5] サービスの確認..."
echo "IT Zone (Grafana):"
kubectl get svc -n it-zone grafana

echo ""
echo "Application Zone (PowSyBl API):"
kubectl get svc -n app-zone powsybl-api

echo ""
echo "=========================================="
echo "テスト完了!"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. Grafana UI: http://localhost:3000 (admin/admin)"
echo "2. PowSyBl API テスト:"
echo "   kubectl port-forward -n app-zone svc/powsybl-api 8000:8000"
echo "   curl http://localhost:8000/stations"
echo ""
