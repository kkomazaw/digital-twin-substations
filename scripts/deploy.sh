#!/bin/bash
set -e

echo "=========================================="
echo "デジタルツイン変電所デモ デプロイメント"
echo "=========================================="

# Kindクラスター作成
echo ""
echo "[1/5] Kindクラスター作成中..."
if kind get clusters | grep -q digital-twin-substation; then
    echo "  クラスターは既に存在します"
else
    DOCKER_HOST=unix:///var/run/podman/podman.sock kind create cluster --config kind-config.yaml
fi

# イメージをKindにロード
echo ""
echo "[2/5] コンテナイメージをKindクラスターにロード中..."
DOCKER_HOST=unix:///var/run/podman/podman.sock kind load docker-image localhost/ied-simulator:latest --name digital-twin-substation
DOCKER_HOST=unix:///var/run/podman/podman.sock kind load docker-image localhost/edge-collector:latest --name digital-twin-substation
DOCKER_HOST=unix:///var/run/podman/podman.sock kind load docker-image localhost/kafka-influxdb-consumer:latest --name digital-twin-substation
DOCKER_HOST=unix:///var/run/podman/podman.sock kind load docker-image localhost/powsybl-api:latest --name digital-twin-substation

# 名前空間作成
echo ""
echo "[3/5] 名前空間作成中..."
kubectl apply -f k8s/ot-zone/ied-deployment.yaml --dry-run=client -o yaml | grep "kind: Namespace" -A 5 | kubectl apply -f -
kubectl apply -f k8s/edge-zone/edge-collector-deployment.yaml --dry-run=client -o yaml | grep "kind: Namespace" -A 5 | kubectl apply -f -
kubectl apply -f k8s/data-zone/namespace.yaml
kubectl apply -f k8s/app-zone/namespace.yaml
kubectl apply -f k8s/it-zone/namespace.yaml

# Data Zoneデプロイ
echo ""
echo "[4/5] Data Zoneコンポーネントをデプロイ中..."
kubectl apply -f k8s/data-zone/

# 他のゾーンをデプロイ
echo ""
echo "Edge Zoneをデプロイ中..."
kubectl apply -f k8s/edge-zone/

echo "OT Zoneをデプロイ中..."
kubectl apply -f k8s/ot-zone/

echo "Application Zoneをデプロイ中..."
kubectl apply -f k8s/app-zone/

echo "IT Zoneをデプロイ中..."
kubectl apply -f k8s/it-zone/

# NetworkPolicyデプロイ
echo ""
echo "[5/5] NetworkPolicyを適用中..."
kubectl apply -f k8s/network-policies/

echo ""
echo "=========================================="
echo "デプロイメント完了!"
echo "=========================================="
echo ""
echo "起動確認: kubectl get pods --all-namespaces"
echo "Grafana UI: http://localhost:3000 (admin/admin)"
echo "PowSyBl API: kubectl port-forward -n app-zone svc/powsybl-api 8000:8000"
echo ""
