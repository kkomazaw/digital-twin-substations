#!/bin/bash
set -e

echo "=========================================="
echo "OpenShift 権限設定"
echo "=========================================="

echo ""
echo "[1/3] ServiceAccountにイメージプル権限を付与..."

# 各ゾーンのServiceAccountに内部レジストリからのプル権限を付与
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    echo "  Granting image-puller role to $zone/default..."
    oc policy add-role-to-user system:image-puller system:serviceaccount:${zone}:default \
      --namespace=digital-twin 2>/dev/null || echo "    Already granted"
done

echo ""
echo "[2/3] InfluxDB/PostgreSQL用のSCC設定..."

# InfluxDBとPostgreSQLは特定のユーザーIDで実行する必要があるため、
# anyuid SCCを付与（開発環境のみ）
echo "  Granting anyuid SCC to data-zone/default..."
oc adm policy add-scc-to-user anyuid -z default -n data-zone 2>/dev/null || echo "    Already granted"

echo ""
echo "[3/3] 既存のPodを削除して再作成..."

# 失敗しているPodを削除（自動的に再作成される）
echo "  Deleting failed pods..."
oc delete pods --field-selector status.phase=Failed --all-namespaces 2>/dev/null || true
oc delete pods -n ot-zone -l app=ied-simulator 2>/dev/null || true
oc delete pods -n edge-zone -l app=edge-collector 2>/dev/null || true
oc delete pods -n data-zone -l app=redis-influxdb-consumer 2>/dev/null || true
oc delete pods -n data-zone -l app=influxdb 2>/dev/null || true
oc delete pods -n data-zone -l app=postgres 2>/dev/null || true
oc delete pods -n app-zone -l app=powsybl-api 2>/dev/null || true

echo ""
echo "=========================================="
echo "権限設定完了!"
echo "=========================================="
echo ""
echo "Podが再作成されるまで30秒待機..."
sleep 30

echo ""
echo "Pod状態確認:"
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"

echo ""
echo "引き続き問題がある場合は、以下を実行してください:"
echo "  ./scripts/diagnose-deployment.sh"
echo ""
