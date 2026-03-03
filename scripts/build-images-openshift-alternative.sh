#!/bin/bash
set -e

echo "=========================================="
echo "OpenShift Local イメージビルド (代替方法)"
echo "=========================================="
echo ""
echo "この方法では、ローカルでビルドしたイメージを"
echo "OpenShiftの内部レジストリを経由せずに直接使用します"
echo ""

PROJECT="digital-twin"

# プロジェクト作成（既存の場合はスキップ）
echo "Creating project if not exists..."
oc new-project ${PROJECT} 2>/dev/null || oc project ${PROJECT}

echo ""
echo "各ゾーンのプロジェクトを作成..."
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    oc new-project ${zone} 2>/dev/null || echo "  Project ${zone} already exists"
done

echo ""
echo "=========================================="
echo "方法1: BuildConfigを使用 (推奨)"
echo "=========================================="
echo ""

# ImageStreamを先に作成
echo "Creating ImageStreams..."
oc create imagestream ied-simulator -n ${PROJECT} 2>/dev/null || echo "  ImageStream ied-simulator already exists"
oc create imagestream edge-collector -n ${PROJECT} 2>/dev/null || echo "  ImageStream edge-collector already exists"
oc create imagestream redis-influxdb-consumer -n ${PROJECT} 2>/dev/null || echo "  ImageStream redis-influxdb-consumer already exists"
oc create imagestream powsybl-api -n ${PROJECT} 2>/dev/null || echo "  ImageStream powsybl-api already exists"

echo ""
# IED Simulator BuildConfig
echo "Creating BuildConfig for IED Simulator..."
cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: ied-simulator
spec:
  output:
    to:
      kind: ImageStreamTag
      name: ied-simulator:latest
  source:
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile
EOF

# Edge Collector BuildConfig
echo "Creating BuildConfig for Edge Collector..."
cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: edge-collector
spec:
  output:
    to:
      kind: ImageStreamTag
      name: edge-collector:latest
  source:
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile
EOF

# Redis-InfluxDB Consumer BuildConfig
echo "Creating BuildConfig for Redis-InfluxDB Consumer..."
cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: redis-influxdb-consumer
spec:
  output:
    to:
      kind: ImageStreamTag
      name: redis-influxdb-consumer:latest
  source:
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile
EOF

# PowSyBl API BuildConfig
echo "Creating BuildConfig for PowSyBl API..."
cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: powsybl-api
spec:
  output:
    to:
      kind: ImageStreamTag
      name: powsybl-api:latest
  source:
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile
EOF

echo ""
echo "Starting builds..."

# IED Simulator
echo ""
echo "Building IED Simulator..."
tar -czf /tmp/ied-simulator.tar.gz -C deployments/ied-simulator .
oc start-build ied-simulator --from-archive=/tmp/ied-simulator.tar.gz --follow -n ${PROJECT}

# Edge Collector
echo ""
echo "Building Edge Collector..."
tar -czf /tmp/edge-collector.tar.gz -C deployments/edge-collector .
oc start-build edge-collector --from-archive=/tmp/edge-collector.tar.gz --follow -n ${PROJECT}

# Redis-InfluxDB Consumer
echo ""
echo "Building Redis-InfluxDB Consumer..."
tar -czf /tmp/redis-influxdb-consumer.tar.gz -C deployments/redis-influxdb-consumer .
oc start-build redis-influxdb-consumer --from-archive=/tmp/redis-influxdb-consumer.tar.gz --follow -n ${PROJECT}

# PowSyBl API
echo ""
echo "Building PowSyBl API..."
tar -czf /tmp/powsybl-api.tar.gz -C deployments/powsybl-api .
oc start-build powsybl-api --from-archive=/tmp/powsybl-api.tar.gz --follow -n ${PROJECT}

# クリーンアップ
rm -f /tmp/ied-simulator.tar.gz /tmp/edge-collector.tar.gz /tmp/redis-influxdb-consumer.tar.gz /tmp/powsybl-api.tar.gz

echo ""
echo "=========================================="
echo "ビルド完了!"
echo "=========================================="
echo ""
echo "ImageStreamを確認:"
oc get imagestreams -n ${PROJECT}
echo ""
echo "次のステップ: デプロイを実行"
echo "  ./scripts/deploy-openshift.sh"
echo ""
