#!/bin/bash
# デジタルツイン変電所 - CRC再起動後の完全デプロイスクリプト
# このスクリプトはCRC再作成後にすべてのコンポーネントを順次デプロイします

set -e

PROJECT_ROOT="/Users/kkomazaw/Development/digital-twin-substations"

echo "=========================================="
echo "デジタルツイン変電所 - 完全デプロイ開始"
echo "=========================================="
echo ""
echo "⚠️  このスクリプトは以下を実行します:"
echo "  1. Namespace/Project作成"
echo "  2. データゾーン（Redis, InfluxDB, PostgreSQL）"
echo "  3. エッジゾーン（Edge Collector, FledgePOWER）"
echo "  4. OTゾーン（IEDシミュレータ）"
echo "  5. アプリケーションゾーン（PowSyBl API）"
echo "  6. ITゾーン（Grafana + ダッシュボード）"
echo "  7. データコンシューマー（Redis→InfluxDB）"
echo ""
read -p "続行しますか? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "キャンセルしました"
    exit 1
fi

cd $PROJECT_ROOT

# CRC環境設定
echo ""
echo "CRC環境設定中..."
source <(crc oc-env)

# ログイン確認
if ! oc whoami &> /dev/null; then
    echo "OpenShiftにログインしてください:"
    echo "  推奨: oc login -u kubeadmin https://api.crc.testing:6443"
    echo "  または: oc login -u developer https://api.crc.testing:6443"
    echo ""
    echo "kubeadminパスワード確認: crc console --credentials"
    exit 1
fi

# 権限チェック（kubeadmin推奨）
CURRENT_USER=$(oc whoami)
if [ "$CURRENT_USER" != "kubeadmin" ]; then
    echo "⚠️  警告: 現在のユーザーは '$CURRENT_USER' です"
    echo "   一部の操作に権限が必要な場合があります"
    echo "   推奨: kubeadmin でログインしてください"
    echo ""
    read -p "このまま続行しますか? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "キャンセルしました"
        echo "kubeadminでログインしてください: oc login -u kubeadmin https://api.crc.testing:6443"
        exit 1
    fi
fi

# ============================================================================
# [1/7] Namespace/Project作成
# ============================================================================
echo ""
echo "=========================================="
echo "[1/7] Namespace/Project作成"
echo "=========================================="

for zone in ot-zone edge-zone data-zone app-zone it-zone; do
    echo "  Creating project: ${zone}"
    oc new-project ${zone} 2>/dev/null || echo "    Project ${zone} already exists"
done

echo "✓ Namespace作成完了"

# ============================================================================
# [2/7] データゾーン（基盤サービス）デプロイ
# ============================================================================
echo ""
echo "=========================================="
echo "[2/7] データゾーン デプロイ"
echo "=========================================="

echo "  anyuid SCC付与..."
oc adm policy add-scc-to-user anyuid -z default -n data-zone 2>/dev/null || echo "    既に付与済み"

echo "  Redis デプロイ..."
oc apply -f openshift/data-zone/redis-deployment.yaml

echo "  InfluxDB デプロイ..."
oc apply -f openshift/data-zone/influxdb-deployment.yaml

echo "  PostgreSQL デプロイ..."
oc apply -f openshift/data-zone/postgres-deployment.yaml

echo "  起動待機中（最大120秒）..."
sleep 10
oc wait --for=condition=ready pod -l app=redis -n data-zone --timeout=60s || echo "    Warning: Redis起動タイムアウト"
oc wait --for=condition=ready pod -l app=influxdb -n data-zone --timeout=60s || echo "    Warning: InfluxDB起動タイムアウト"

echo "✓ データゾーン デプロイ完了"

# ============================================================================
# [3/7] エッジゾーン デプロイ
# ============================================================================
echo ""
echo "=========================================="
echo "[3/7] エッジゾーン デプロイ"
echo "=========================================="

echo "  Edge Collector デプロイ..."
oc apply -f openshift/edge-zone/edge-collector-deployment.yaml

echo "  FledgePOWER デプロイ..."
oc apply -f openshift/edge-zone/fledgepower-deployment.yaml

echo "✓ エッジゾーン デプロイ完了"

# ============================================================================
# [4/7] OTゾーン デプロイ
# ============================================================================
echo ""
echo "=========================================="
echo "[4/7] OTゾーン デプロイ"
echo "=========================================="

echo "  IEDシミュレータ デプロイ..."
oc apply -f openshift/ot-zone/ied-deployment.yaml

echo "✓ OTゾーン デプロイ完了"

# ============================================================================
# [5/7] アプリケーションゾーン デプロイ（BuildConfig作成→ビルド）
# ============================================================================
echo ""
echo "=========================================="
echo "[5/7] アプリケーションゾーン デプロイ"
echo "=========================================="

echo "  PowSyBl API BuildConfig/ImageStream/Deployment作成..."
oc apply -f openshift/app-zone/powsybl-api-deployment.yaml

echo "  PowSyBl API イメージビルド中（5-10分かかります）..."
tar -czf /tmp/powsybl-api.tar.gz -C deployments/powsybl-api .

# ビルド開始（タイムアウト対策：followなし）
oc start-build powsybl-api \
  --from-archive=/tmp/powsybl-api.tar.gz \
  --namespace=app-zone

# ビルド完了待機
echo "  ビルド完了待機中..."
BUILD_NAME=$(oc get builds -n app-zone --sort-by=.metadata.creationTimestamp -o name | tail -1)
oc wait --for=condition=Complete ${BUILD_NAME} -n app-zone --timeout=600s || {
    echo "  ⚠️  ビルドがタイムアウトしました。手動で確認してください:"
    echo "     oc get builds -n app-zone"
    echo "     oc logs ${BUILD_NAME} -n app-zone"
}

# ImageStreamタグ確認
echo "  ImageStream確認..."
oc get is powsybl-api -n app-zone

# Pod起動待機
echo "  PowSyBl API Pod起動待機..."
oc delete pod -l app=powsybl-api -n app-zone --ignore-not-found=true
sleep 10
oc wait --for=condition=Ready pod -l app=powsybl-api -n app-zone --timeout=180s || echo "    Warning: Pod起動タイムアウト"

rm -f /tmp/powsybl-api.tar.gz

echo "✓ アプリケーションゾーン デプロイ完了"

# ============================================================================
# [6/7] ITゾーン デプロイ（Grafana + ダッシュボード）
# ============================================================================
echo ""
echo "=========================================="
echo "[6/7] ITゾーン デプロイ"
echo "=========================================="

echo "  Grafana ダッシュボード ConfigMap作成..."
oc apply -f openshift/it-zone/grafana-topology-dashboard.yaml
oc apply -f openshift/it-zone/grafana-powerflow-dashboard.yaml
oc apply -f openshift/it-zone/grafana-analysis-dashboard.yaml

echo "  Grafana デプロイ..."
oc apply -f openshift/it-zone/grafana-deployment.yaml

echo "  Grafana Pod起動待機..."
sleep 10
oc wait --for=condition=Ready pod -l app=grafana -n it-zone --timeout=120s || echo "    Warning: Grafana起動タイムアウト"

echo "✓ ITゾーン デプロイ完了"

# ============================================================================
# [7/7] データコンシューマー デプロイ
# ============================================================================
echo ""
echo "=========================================="
echo "[7/7] データコンシューマー デプロイ"
echo "=========================================="

echo "  Redis-InfluxDB Consumer デプロイ..."
oc apply -f openshift/data-zone/redis-influxdb-consumer-deployment.yaml

echo "✓ データコンシューマー デプロイ完了"

# ============================================================================
# デプロイ状態確認
# ============================================================================
echo ""
echo "=========================================="
echo "デプロイ完了 - 状態確認"
echo "=========================================="

echo ""
echo "全Podの状態:"
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)" || echo "No pods found"

echo ""
echo "=========================================="
echo "✓ 完全デプロイ完了"
echo "=========================================="

# Routes取得
GRAFANA_ROUTE=$(oc get route grafana -n it-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")
POWSYBL_ROUTE=$(oc get route powsybl-api -n app-zone -o jsonpath='{.spec.host}' 2>/dev/null || echo "未作成")

echo ""
echo "アクセスURL:"
echo "  Grafana:      http://${GRAFANA_ROUTE}"
echo "                ログイン: admin / admin"
echo ""
echo "  PowSyBl API:  http://${POWSYBL_ROUTE}"
echo "                API Docs: http://${POWSYBL_ROUTE}/docs"
echo ""
echo "ダッシュボード:"
echo "  - Substation Overview (変電所概要)"
echo "  - Substation Data Flow Topology (データフロートポロジー)"
echo "  - Power Flow Analysis (PowSyBl) (潮流分析)"
echo "  - PowSyBl Advanced Analysis Results (高度分析結果)"
echo ""
echo "監視コマンド:"
echo "  全Pod確認:    oc get pods --all-namespaces | grep zone"
echo "  ログ確認:     oc logs -f <pod-name> -n <namespace>"
echo "  Route確認:    oc get routes --all-namespaces"
echo ""
echo "トラブルシューティング:"
echo "  Pod再起動:    oc delete pod <pod-name> -n <namespace>"
echo "  ビルド確認:   oc get builds -n app-zone"
echo "  ログ確認:     oc logs build/<build-name> -n app-zone"
echo ""
