#!/bin/bash
set -e

echo "=========================================="
echo "OpenShift Local 内部レジストリ設定"
echo "=========================================="
echo ""
echo "このスクリプトはkubeadminユーザーで実行する必要があります。"
echo ""

# 現在のユーザーを確認
CURRENT_USER=$(oc whoami 2>/dev/null || echo "not-logged-in")

if [ "$CURRENT_USER" != "kubeadmin" ]; then
    echo "現在のユーザー: $CURRENT_USER"
    echo ""
    echo "kubeadminでログインしてください:"
    echo ""
    echo "  oc login -u kubeadmin https://api.crc.testing:6443"
    echo ""
    echo "パスワードは 'crc start' 実行時に表示されます。"
    echo "または、以下のコマンドで確認できます:"
    echo ""
    echo "  crc console --credentials"
    echo ""
    exit 1
fi

echo "✓ kubeadminユーザーでログインしています"
echo ""

# 内部レジストリのデフォルトルートを有効化
echo "内部レジストリのデフォルトルートを有効化中..."
oc patch configs.imageregistry.operator.openshift.io/cluster \
  --patch '{"spec":{"defaultRoute":true}}' \
  --type=merge

echo "Waiting for registry route to be ready..."
sleep 5

# レジストリルートの確認
echo ""
echo "レジストリルートを確認中..."
REGISTRY_ROUTE=$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -z "$REGISTRY_ROUTE" ]; then
    echo "Warning: レジストリルートがまだ作成されていません。もう少し待ってから確認してください。"
    echo ""
    echo "確認コマンド:"
    echo "  oc get route default-route -n openshift-image-registry"
else
    echo "✓ レジストリルート: $REGISTRY_ROUTE"
fi

echo ""
echo "=========================================="
echo "設定完了!"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. developerユーザーに戻る:"
echo "   oc login -u developer https://api.crc.testing:6443"
echo ""
echo "2. イメージをビルド・プッシュ:"
echo "   ./scripts/build-images-openshift.sh"
echo ""
