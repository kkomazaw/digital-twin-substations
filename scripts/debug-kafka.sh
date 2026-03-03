#!/bin/bash

echo "=========================================="
echo "Kafka トラブルシューティング"
echo "=========================================="
echo ""

echo "1. Pod状態確認:"
oc get pods -n data-zone -l app=kafka

echo ""
echo "2. Pod詳細:"
oc describe pod -n data-zone -l app=kafka | tail -50

echo ""
echo "3. イベント確認:"
oc get events -n data-zone --sort-by='.lastTimestamp' | grep -i kafka | tail -10

echo ""
echo "4. リソース確認:"
oc get nodes -o yaml | grep -A 10 "allocatable:"

echo ""
echo "5. Deployment設定確認:"
oc get deployment kafka -n data-zone -o yaml | grep -A 5 "resources:"

echo ""
read -p "Podログを確認しますか? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "6. Pod ログ:"
    oc logs -n data-zone -l app=kafka --tail=100 || echo "ログが取得できません（Podが起動していない可能性）"
fi
