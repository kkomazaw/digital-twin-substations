#!/bin/bash
set -e

echo "OpenShift Localのプロジェクトをクリーンアップ中..."

# 全ゾーンのプロジェクトを削除
for zone in ot-zone edge-zone data-zone app-zone it-zone digital-twin; do
    echo "  Deleting project ${zone}..."
    oc delete project ${zone} --ignore-not-found=true
done

echo "クリーンアップ完了!"
echo ""
echo "Note: OpenShift Local自体を停止する場合は 'crc stop' を実行してください"
