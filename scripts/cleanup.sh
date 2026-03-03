#!/bin/bash
set -e

echo "クリーンアップ中..."

# Kindクラスター削除
echo "Kindクラスターを削除..."
DOCKER_HOST=unix:///var/run/podman/podman.sock kind delete cluster --name digital-twin-substation

echo "クリーンアップ完了!"
