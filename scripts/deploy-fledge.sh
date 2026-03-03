#!/bin/bash
set -e

echo "========================================="
echo " FledgePOWER Integration Deployment"
echo "========================================="
echo ""

PROJECT="digital-twin"

# プロジェクト存在確認
if ! oc project ${PROJECT} &> /dev/null; then
    echo "Creating project ${PROJECT}..."
    oc new-project ${PROJECT}
fi

# FledgePOWER Gatewayイメージビルド
echo "Building FledgePOWER Gateway image..."
cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: fledgepower-gateway
  namespace: ${PROJECT}
EOF

cat <<EOF | oc apply -n ${PROJECT} -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: fledgepower-gateway
  namespace: ${PROJECT}
spec:
  output:
    to:
      kind: ImageStreamTag
      name: fledgepower-gateway:latest
  source:
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile
EOF

echo "Starting build for fledgepower-gateway..."
tar -czf /tmp/fledgepower-gateway.tar.gz -C deployments/fledgepower-gateway .
oc start-build fledgepower-gateway --from-archive=/tmp/fledgepower-gateway.tar.gz --follow -n digital-twin
rm -f /tmp/fledgepower-gateway.tar.gz

# IED Simulatorイメージ再ビルド（HTTPサーバー対応）
echo ""
echo "Rebuilding IED Simulator with HTTP server support..."
tar -czf /tmp/ied-simulator.tar.gz -C deployments/ied-simulator .
oc start-build ied-simulator --from-archive=/tmp/ied-simulator.tar.gz --follow -n digital-twin
rm -f /tmp/ied-simulator.tar.gz

# FledgePOWER Gateway デプロイ
echo ""
echo "Deploying FledgePOWER Gateway..."
oc apply -f openshift/edge-zone/fledgepower-deployment.yaml

# NetworkPolicy適用
echo ""
echo "Applying NetworkPolicy for Fledge..."
oc apply -f k8s/network-policies/edge-zone-fledge-policy.yaml

# IED Simulator更新（HTTPポート追加）
echo ""
echo "Updating IED Simulator deployment..."
oc apply -f openshift/ot-zone/ied-deployment.yaml

echo ""
echo "========================================="
echo " Waiting for pods to be ready..."
echo "========================================="

# Podの起動待機
oc wait --for=condition=ready pod -l app=fledgepower-gateway -n edge-zone --timeout=120s || true
oc wait --for=condition=ready pod -l app=ied-simulator -n ot-zone --timeout=120s || true

echo ""
echo "========================================="
echo " FledgePOWER Integration Deployment Complete!"
echo "========================================="
echo ""
echo "Access FledgePOWER GUI:"
FLEDGE_URL=$(oc get route fledgepower-gui -n edge-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not yet available")
echo "  http://${FLEDGE_URL}"
echo ""
echo "Check Pod status:"
echo "  oc get pods -n edge-zone"
echo "  oc get pods -n ot-zone"
echo ""
echo "View logs:"
echo "  oc logs -n edge-zone -l app=fledgepower-gateway -f"
echo ""
echo "Test IED HTTP endpoint:"
echo "  oc exec -n edge-zone deployment/fledgepower-gateway -- curl http://ied-simulator.ot-zone:8080/telemetry"
echo ""
