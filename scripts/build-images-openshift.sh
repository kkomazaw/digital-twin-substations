#!/bin/bash
set -e

echo "Building container images for OpenShift Local..."

PROJECT="digital-twin"

echo "OpenShift Localにログインしていることを確認してください"
echo "oc login -u developer https://api.crc.testing:6443"
echo ""

# プロジェクト作成（既存の場合はスキップ）
echo "Creating project if not exists..."
oc new-project ${PROJECT} 2>/dev/null || oc project ${PROJECT}

echo ""
echo "Checking internal registry route..."

# 環境変数でレジストリホストが指定されている場合はそれを使用
if [ -n "$REGISTRY_HOST" ]; then
    echo "Using REGISTRY_HOST from environment: ${REGISTRY_HOST}"
else
    # レジストリルートから取得を試みる
    REGISTRY_HOST=$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null)

    if [ -z "$REGISTRY_HOST" ]; then
        echo ""
        echo "ERROR: レジストリホストを取得できませんでした。"
        echo ""
        echo "以下のいずれかの方法で対処してください:"
        echo ""
        echo "方法1: kubeadminでレジストリホストを確認して環境変数で指定"
        echo ""
        echo "  # kubeadminでログイン"
        echo "  oc login -u kubeadmin https://api.crc.testing:6443"
        echo ""
        echo "  # レジストリホストを確認"
        echo "  REGISTRY_HOST=\$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}')"
        echo "  echo \$REGISTRY_HOST"
        echo ""
        echo "  # developerでログインし直す"
        echo "  oc login -u developer https://api.crc.testing:6443"
        echo ""
        echo "  # 環境変数を設定してスクリプト実行"
        echo "  REGISTRY_HOST=\$REGISTRY_HOST ./scripts/build-images-openshift.sh"
        echo ""
        echo "方法2: デフォルトのホスト名を使用"
        echo ""
        echo "  REGISTRY_HOST=default-route-openshift-image-registry.apps-crc.testing ./scripts/build-images-openshift.sh"
        echo ""
        exit 1
    fi
fi

echo "✓ Registry host: ${REGISTRY_HOST}"

# Podmanでログイン
echo ""
echo "Logging into OpenShift internal registry..."
TOKEN=$(oc whoami -t)
podman login -u developer -p ${TOKEN} ${REGISTRY_HOST} --tls-verify=false

echo ""
echo "Creating ImageStreams..."
# ImageStreamを事前に作成
for app in ied-simulator edge-collector kafka-influxdb-consumer powsybl-api; do
    oc create imagestream ${app} -n ${PROJECT} 2>/dev/null || echo "  ImageStream ${app} already exists"
done

# IED Simulator
echo ""
echo "Building and pushing IED Simulator..."
podman build -t ${REGISTRY_HOST}/${PROJECT}/ied-simulator:latest -f deployments/ied-simulator/Dockerfile deployments/ied-simulator/
podman push ${REGISTRY_HOST}/${PROJECT}/ied-simulator:latest --tls-verify=false

# Edge Collector
echo ""
echo "Building and pushing Edge Collector..."
podman build -t ${REGISTRY_HOST}/${PROJECT}/edge-collector:latest -f deployments/edge-collector/Dockerfile deployments/edge-collector/
podman push ${REGISTRY_HOST}/${PROJECT}/edge-collector:latest --tls-verify=false

# Kafka-InfluxDB Consumer
echo ""
echo "Building and pushing Kafka-InfluxDB Consumer..."
podman build -t ${REGISTRY_HOST}/${PROJECT}/kafka-influxdb-consumer:latest -f deployments/kafka-influxdb-consumer/Dockerfile deployments/kafka-influxdb-consumer/
podman push ${REGISTRY_HOST}/${PROJECT}/kafka-influxdb-consumer:latest --tls-verify=false

# PowSyBl API
echo ""
echo "Building and pushing PowSyBl API..."
podman build -t ${REGISTRY_HOST}/${PROJECT}/powsybl-api:latest -f deployments/powsybl-api/Dockerfile deployments/powsybl-api/
podman push ${REGISTRY_HOST}/${PROJECT}/powsybl-api:latest --tls-verify=false

echo ""
echo "All images built and pushed successfully!"
oc get imagestreams -n ${PROJECT}
