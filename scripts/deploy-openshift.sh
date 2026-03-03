#!/bin/bash
set -e

echo "=========================================="
echo "デジタルツイン変電所デモ デプロイメント"
echo "OpenShift Local版"
echo "=========================================="

# OpenShift Localにログイン確認
if ! oc whoami &> /dev/null; then
    echo "Error: OpenShift Localにログインしてください"
    echo "  crc start"
    echo "  eval \$(crc oc-env)"
    echo "  oc login -u developer https://api.crc.testing:6443"
    exit 1
fi

PROJECT="digital-twin"

echo ""
echo "[1/7] プロジェクト作成..."
oc new-project ${PROJECT} 2>/dev/null || oc project ${PROJECT}

# 各ゾーンの名前空間を作成（OpenShiftではプロジェクトとして作成）
echo ""
echo "[2/7] ゾーン（名前空間）作成..."
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    oc new-project ${zone} 2>/dev/null || echo "  Project ${zone} already exists"
done

# ImageStreamの確認
echo ""
echo "[3/7] ImageStreamの確認..."
echo "digital-twin プロジェクトのImageStream:"
oc get imagestreams -n ${PROJECT} 2>/dev/null || echo "  Warning: ImageStreamが見つかりません"
echo ""
echo "イメージがビルドされていない場合は、以下を実行してください:"
echo "  ./scripts/build-images-openshift-alternative.sh"
echo ""
read -p "続行しますか? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "[4/7] Data Zoneコンポーネントをデプロイ中..."
oc project data-zone

# ラベルを追加（namespace.yamlの代わり）
oc label namespace data-zone zone=data iec62443=data-layer --overwrite 2>/dev/null || true

# OpenShift用マニフェストを使用
oc apply -f openshift/data-zone/redis-deployment.yaml
oc apply -f openshift/data-zone/influxdb-deployment.yaml
oc apply -f openshift/data-zone/postgres-deployment.yaml

# Redisの起動を待つ
echo "  Redisの起動を待っています（最大2分）..."
oc wait --for=condition=ready pod -l app=redis -n data-zone --timeout=120s || echo "  Warning: Redisがまだ起動していません"

# Redis-InfluxDB Consumerをデプロイ
echo "  Redis-InfluxDB Consumerをデプロイ..."
oc apply -f openshift/data-zone/redis-influxdb-consumer-deployment.yaml

echo ""
echo "[5/7] Edge Zoneをデプロイ中..."
oc project edge-zone
oc label namespace edge-zone zone=edge iec62443=level-3 --overwrite 2>/dev/null || true
oc apply -f openshift/edge-zone/edge-collector-deployment.yaml

echo ""
echo "OT Zoneをデプロイ中..."
oc project ot-zone
oc label namespace ot-zone zone=ot iec62443=level-0-2 --overwrite 2>/dev/null || true
oc apply -f openshift/ot-zone/ied-deployment.yaml

echo ""
echo "Application Zoneをデプロイ中..."
oc project app-zone
oc label namespace app-zone zone=application iec62443=application-layer --overwrite 2>/dev/null || true
oc apply -f openshift/app-zone/powsybl-api-deployment.yaml

# PowSyBl API用のRouteを作成
echo "  Creating Route for PowSyBl API..."
oc expose svc/powsybl-api -n app-zone 2>/dev/null || echo "  Route already exists"

echo ""
echo "IT Zoneをデプロイ中..."
oc project it-zone
oc label namespace it-zone zone=it iec62443=it-layer --overwrite 2>/dev/null || true
oc apply -f openshift/it-zone/grafana-deployment.yaml

# Grafana用のRouteを作成
echo "  Creating Route for Grafana..."
oc expose svc/grafana -n it-zone 2>/dev/null || echo "  Route already exists"

echo ""
echo "[6/7] NetworkPolicyを適用中..."
# NetworkPolicyはOpenShiftでも動作するので適用
oc apply -f k8s/network-policies/ -n ot-zone 2>/dev/null || echo "  NetworkPolicy適用をスキップ (ot-zone)"
oc apply -f k8s/network-policies/ -n edge-zone 2>/dev/null || echo "  NetworkPolicy適用をスキップ (edge-zone)"
oc apply -f k8s/network-policies/ -n data-zone 2>/dev/null || echo "  NetworkPolicy適用をスキップ (data-zone)"
oc apply -f k8s/network-policies/ -n app-zone 2>/dev/null || echo "  NetworkPolicy適用をスキップ (app-zone)"
oc apply -f k8s/network-policies/ -n it-zone 2>/dev/null || echo "  NetworkPolicy適用をスキップ (it-zone)"

echo ""
echo "[7/7] デプロイメント状態確認..."
echo ""
echo "全Podの状態:"
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)" || true

echo ""
echo "=========================================="
echo "デプロイメント完了!"
echo "=========================================="
echo ""
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")
echo "Grafana UI: http://${GRAFANA_URL} (admin/admin)"
echo "PowSyBl API: http://${API_URL}"
echo ""
echo "Pod起動確認: oc get pods --all-namespaces"
echo "ログ確認: oc logs -n <namespace> <pod-name>"
echo ""
