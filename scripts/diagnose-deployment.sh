#!/bin/bash

echo "=========================================="
echo "デプロイメント診断"
echo "=========================================="

echo ""
echo "1. ImageStreamの確認:"
oc get imagestreams -n digital-twin

echo ""
echo "2. ImageStreamの詳細（タグ確認）:"
for is in ied-simulator edge-collector redis-influxdb-consumer powsybl-api; do
    echo "--- $is ---"
    oc get imagestream $is -n digital-twin -o jsonpath='{.status.tags[*].tag}' 2>/dev/null && echo "" || echo "  Not found"
done

echo ""
echo "3. 失敗しているPodの詳細（1つ確認）:"
echo "--- IED Simulator ---"
POD=$(oc get pods -n ot-zone -l app=ied-simulator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    oc describe pod $POD -n ot-zone | grep -A 10 "Events:"
fi

echo ""
echo "--- Edge Collector ---"
POD=$(oc get pods -n edge-zone -l app=edge-collector -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    oc describe pod $POD -n edge-zone | grep -A 10 "Events:"
fi

echo ""
echo "4. InfluxDBのクラッシュ原因:"
POD=$(oc get pods -n data-zone -l app=influxdb -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    oc logs $POD -n data-zone --tail=50 2>&1 | head -20
fi

echo ""
echo "5. PostgreSQLのクラッシュ原因:"
POD=$(oc get pods -n data-zone -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    oc logs $POD -n data-zone --tail=50 2>&1 | head -20
fi

echo ""
echo "6. BuildConfigの状態:"
oc get builds -n digital-twin | tail -10

echo ""
echo "=========================================="
