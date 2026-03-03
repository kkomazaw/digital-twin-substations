#!/bin/bash
set -e

echo "=========================================="
echo "Complete Redeployment for OpenShift Local"
echo "=========================================="

# Create all projects
echo ""
echo "[1/5] Creating projects..."
oc new-project digital-twin 2>/dev/null || oc project digital-twin
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    oc new-project ${zone} 2>/dev/null || echo "  Project ${zone} already exists"
done

# Rebuild container images
echo ""
echo "[2/5] Rebuilding container images..."
cd "$(dirname "$0")/.."

# Create ImageStreams
echo "  Creating ImageStreams..."
oc create imagestream ied-simulator -n digital-twin 2>/dev/null || echo "    ImageStream ied-simulator exists"
oc create imagestream edge-collector -n digital-twin 2>/dev/null || echo "    ImageStream edge-collector exists"
oc create imagestream redis-influxdb-consumer -n digital-twin 2>/dev/null || echo "    ImageStream redis-influxdb-consumer exists"
oc create imagestream powsybl-api -n digital-twin 2>/dev/null || echo "    ImageStream powsybl-api exists"

# Create BuildConfigs
echo "  Creating BuildConfigs..."

cat <<EOF | oc apply -n digital-twin -f -
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
---
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
---
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
---
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

# Build images
echo ""
echo "  Building images (this takes ~5 minutes)..."

echo "    - IED Simulator..."
tar -czf /tmp/ied-simulator.tar.gz -C deployments/ied-simulator .
oc start-build ied-simulator --from-archive=/tmp/ied-simulator.tar.gz --follow -n digital-twin

echo "    - Edge Collector..."
tar -czf /tmp/edge-collector.tar.gz -C deployments/edge-collector .
oc start-build edge-collector --from-archive=/tmp/edge-collector.tar.gz --follow -n digital-twin

echo "    - Redis-InfluxDB Consumer..."
tar -czf /tmp/redis-influxdb-consumer.tar.gz -C deployments/redis-influxdb-consumer .
oc start-build redis-influxdb-consumer --from-archive=/tmp/redis-influxdb-consumer.tar.gz --follow -n digital-twin

echo "    - PowSyBl API..."
tar -czf /tmp/powsybl-api.tar.gz -C deployments/powsybl-api .
oc start-build powsybl-api --from-archive=/tmp/powsybl-api.tar.gz --follow -n digital-twin

# Cleanup
rm -f /tmp/*.tar.gz

# Configure permissions
echo ""
echo "[3/5] Configuring permissions..."

# Grant image-puller role
for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    oc policy add-role-to-user system:image-puller system:serviceaccount:${zone}:default \
      --namespace=digital-twin 2>/dev/null || echo "  Image-puller role already granted to $zone"
done

# Grant anyuid SCC for databases
oc adm policy add-scc-to-user anyuid -z default -n data-zone 2>/dev/null || echo "  anyuid SCC already granted"

# Deploy services
echo ""
echo "[4/5] Deploying services..."

echo "  Data Zone..."
oc apply -f openshift/data-zone/redis-deployment.yaml
oc apply -f openshift/data-zone/influxdb-deployment.yaml
oc apply -f openshift/data-zone/postgres-deployment.yaml

echo "  Waiting for Redis and InfluxDB to start..."
oc wait --for=condition=ready pod -l app=redis -n data-zone --timeout=60s || echo "  Warning: Redis not ready yet"
oc wait --for=condition=ready pod -l app=influxdb -n data-zone --timeout=60s || echo "  Warning: InfluxDB not ready yet"

echo "  Deploying Redis-InfluxDB Consumer..."
oc apply -f openshift/data-zone/redis-influxdb-consumer-deployment.yaml

echo "  Edge Zone..."
oc apply -f openshift/edge-zone/edge-collector-deployment.yaml

echo "  OT Zone..."
oc apply -f openshift/ot-zone/ied-deployment.yaml

echo "  Application Zone..."
oc apply -f openshift/app-zone/powsybl-api-deployment.yaml
oc expose svc/powsybl-api -n app-zone 2>/dev/null || echo "  Route already exists"

echo "  IT Zone..."
oc apply -f openshift/it-zone/grafana-deployment.yaml
oc expose svc/grafana -n it-zone 2>/dev/null || echo "  Route already exists"

# Check status
echo ""
echo "[5/5] Deployment status..."
sleep 10
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
GRAFANA_URL=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "not-created")
API_URL=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "not-created")
echo "Grafana UI: http://${GRAFANA_URL} (admin/admin)"
echo "PowSyBl API: http://${API_URL}"
echo ""
echo "Monitor pods: oc get pods --all-namespaces | grep zone"
echo ""
