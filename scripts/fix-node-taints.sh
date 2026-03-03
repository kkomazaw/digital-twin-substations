#!/bin/bash
set -e

echo "=========================================="
echo "ノードTaint修正"
echo "=========================================="

echo ""
echo "1. 現在のノード状態とTaintを確認:"
oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

echo ""
echo "2. Taintを削除（必要な場合）:"

# CRCノードのTaintを確認
TAINTS=$(oc get nodes -o jsonpath='{.items[0].spec.taints}')

if [ "$TAINTS" != "null" ] && [ -n "$TAINTS" ]; then
    echo "  Taintが検出されました。削除します..."

    # ノード名を取得
    NODE_NAME=$(oc get nodes -o jsonpath='{.items[0].metadata.name}')
    echo "  Node: $NODE_NAME"

    # よくあるTaintを削除
    oc adm taint nodes $NODE_NAME node.kubernetes.io/not-ready- 2>/dev/null || echo "    not-ready taint not found"
    oc adm taint nodes $NODE_NAME node.kubernetes.io/unreachable- 2>/dev/null || echo "    unreachable taint not found"
    oc adm taint nodes $NODE_NAME node.kubernetes.io/disk-pressure- 2>/dev/null || echo "    disk-pressure taint not found"
    oc adm taint nodes $NODE_NAME node.kubernetes.io/memory-pressure- 2>/dev/null || echo "    memory-pressure taint not found"
    oc adm taint nodes $NODE_NAME node.kubernetes.io/pid-pressure- 2>/dev/null || echo "    pid-pressure taint not found"
    oc adm taint nodes $NODE_NAME node.kubernetes.io/network-unavailable- 2>/dev/null || echo "    network-unavailable taint not found"

    # カスタムTaintがある場合は手動で削除が必要
    echo ""
    echo "  削除後のTaint状態:"
    oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
else
    echo "  Taintは設定されていません。"
fi

echo ""
echo "3. Podの再スケジューリング:"
echo "  保留中のPodを削除して再作成..."

# 保留中のPodを削除
oc delete pods --field-selector status.phase=Pending --all-namespaces 2>/dev/null || true

echo ""
echo "=========================================="
echo "修正完了!"
echo "=========================================="
echo ""
echo "30秒待機してPod状態を確認..."
sleep 30

echo ""
echo "Pod状態:"
oc get pods --all-namespaces | grep -E "(ot-zone|edge-zone|data-zone|app-zone|it-zone)"

echo ""
