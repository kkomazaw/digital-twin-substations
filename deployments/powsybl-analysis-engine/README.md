# PowSyBl Advanced Analysis Engine

変電所デジタルツイン向けの高度な電力系統分析・シミュレーションエンジン

## 概要

PowSyBl (Power System Blocks) フレームワークを活用し、以下の高度な電力系統解析機能を提供します：

- **Load Flow Analysis (潮流計算)**: AC/DC潮流計算、電圧プロファイル、損失計算
- **Security Analysis (セキュリティ分析)**: N-1/N-K分析、コンティンジェンシー評価
- **Sensitivity Analysis (感度分析)**: PTDF, PSDF, DCDF等の感度係数計算
- **Optimal Power Flow (最適潮流)**: 発電コスト最小化、制約条件下での最適運用
- **Dynamic Simulation (動的シミュレーション)**: 過渡現象、系統安定性評価
- **Short-Circuit Analysis (短絡分析)**: 短絡電流計算、保護協調

## アーキテクチャ

```
FastAPI REST API (Port 8001)
    ↓
PyPowSyBl Analysis Core
    ├── Network Model Manager
    ├── Load Flow Engine
    ├── Security Analysis Engine
    ├── Sensitivity Analysis Engine
    └── Optimization Engine
    ↓
Data Sources
    ├── InfluxDB (テレメトリー)
    ├── Redis (リアルタイムデータ)
    └── PostgreSQL (分析結果保存)
```

## ディレクトリ構成

```
powsybl-analysis-engine/
├── Dockerfile
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI メインアプリケーション
│   ├── models/              # データモデル
│   │   ├── __init__.py
│   │   ├── network.py       # ネットワークモデル
│   │   ├── loadflow.py      # 潮流計算モデル
│   │   ├── security.py      # セキュリティ分析モデル
│   │   └── sensitivity.py   # 感度分析モデル
│   └── services/            # ビジネスロジック
│       ├── __init__.py
│       ├── network_service.py
│       ├── loadflow_service.py
│       ├── security_service.py
│       └── sensitivity_service.py
└── tests/
```

## API エンドポイント

### ヘルスチェック

```bash
GET /
```

### ネットワーク管理

```bash
# ネットワークリスト取得
GET /networks

# ネットワーク情報取得
GET /networks/{network_id}/info

# サンプルネットワーク作成
POST /networks/create-sample/{network_id}
```

### 潮流計算

```bash
POST /api/v1/loadflow

# リクエスト例
{
  "network_id": "ieee14",
  "parameters": {
    "voltage_init_mode": "UNIFORM_VALUES",
    "transformer_voltage_control_on": true,
    "phase_shifter_regulation_on": true,
    "dc": false
  }
}
```

### セキュリティ分析

```bash
POST /api/v1/security

# リクエスト例
{
  "network_id": "ieee14",
  "contingencies": [
    {
      "id": "N1_LINE_L1-5",
      "elements": ["L1-5-1"]
    }
  ]
}

# N-1コンティンジェンシー自動生成
GET /api/v1/security/{network_id}/n1-contingencies
```

### 感度分析

```bash
POST /api/v1/sensitivity

# リクエスト例
{
  "network_id": "ieee14",
  "factors": [
    {
      "function_type": "BRANCH_ACTIVE_POWER",
      "function_id": "L1-2-1",
      "variable_type": "INJECTION_ACTIVE_POWER",
      "variable_id": "B1-G",
      "variable_set": false
    }
  ],
  "parameters": {
    "analysis_type": "DC"
  }
}

# PTDF係数自動生成
POST /api/v1/sensitivity/{network_id}/generate-ptdf
{
  "monitored_branches": ["L1-2-1", "L1-5-1"],
  "injection_points": ["B1-G", "B2-G"]
}
```

### 包括的分析

```bash
# 潮流計算 → セキュリティ分析を一括実行
POST /api/v1/comprehensive-analysis/{network_id}
```

## ローカル開発

### 前提条件

- Python 3.11+
- pip

### セットアップ

```bash
cd deployments/powsybl-analysis-engine

# 依存関係インストール
pip install -r requirements.txt

# アプリケーション起動
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### APIドキュメント

起動後、以下のURLでインタラクティブなAPIドキュメントにアクセスできます：

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## OpenShift デプロイ

### イメージビルド

```bash
# プロジェクトルートから
cd /Users/kkomazaw/Development/digital-twin-substations

# アーカイブ作成
tar -czf /tmp/powsybl-analysis.tar.gz -C deployments/powsybl-analysis-engine .

# OpenShiftでビルド
oc start-build powsybl-analysis \
  --from-archive=/tmp/powsybl-analysis.tar.gz \
  --follow \
  --namespace=app-zone
```

### デプロイ

```bash
# デプロイメント適用
oc apply -f openshift/app-zone/powsybl-analysis-deployment.yaml

# 状態確認
oc get pods -n app-zone -l app=powsybl-analysis
```

### 自動デプロイスクリプト

```bash
./scripts/deploy-powsybl-analysis.sh
```

## 使用例

### 1. サンプルネットワークで潮流計算

```bash
# サンプルネットワーク作成
curl -X POST http://localhost:8001/networks/create-sample/ieee14

# 潮流計算実行
curl -X POST http://localhost:8001/api/v1/loadflow \
  -H "Content-Type: application/json" \
  -d '{
    "network_id": "ieee14",
    "parameters": {
      "dc": false
    }
  }'
```

### 2. N-1セキュリティ分析

```bash
# N-1コンティンジェンシー生成
curl http://localhost:8001/api/v1/security/ieee14/n1-contingencies > contingencies.json

# セキュリティ分析実行
curl -X POST http://localhost:8001/api/v1/security \
  -H "Content-Type: application/json" \
  -d @contingencies.json
```

### 3. PTDF感度分析

```bash
# PTDF係数生成
curl -X POST http://localhost:8001/api/v1/sensitivity/ieee14/generate-ptdf \
  -H "Content-Type: application/json" \
  -d '{
    "monitored_branches": ["L1-2-1", "L2-3-1"],
    "injection_points": ["B1-G", "B2-G"]
  }' > ptdf_factors.json

# 感度分析実行
curl -X POST http://localhost:8001/api/v1/sensitivity \
  -H "Content-Type: application/json" \
  -d @ptdf_factors.json
```

## パフォーマンス

- **Load Flow計算**: < 5秒 (1000ノードネットワーク)
- **Security Analysis (N-1)**: < 30秒 (100コンティンジェンシー)
- **Sensitivity Analysis**: < 10秒 (1000ファクター)

## トラブルシューティング

### ログ確認

```bash
# OpenShift環境
oc logs -f deployment/powsybl-analysis -n app-zone

# ローカル環境
# アプリケーションログは標準出力に出力されます
```

### 一般的な問題

1. **ネットワークが見つからない**
   - サンプルネットワークを作成: `POST /networks/create-sample/ieee14`

2. **潮流計算が収束しない**
   - パラメータ調整: `voltage_init_mode`, `max_iterations`を変更

3. **メモリ不足**
   - リソース制限を増やす: deployment yamlの`resources.limits.memory`を調整

## 関連ドキュメント

- [PowSyBl公式ドキュメント](https://powsybl.readthedocs.io/)
- [PyPowSyBl APIリファレンス](https://powsybl.readthedocs.io/projects/pypowsybl/)
- [設計ドキュメント](../../docs/POWSYBL_ADVANCED_ANALYSIS.md)

## ライセンス

このプロジェクトはオープンソースです。

## 貢献

バグ報告や機能要望は、GitHubのIssueにて受け付けています。
