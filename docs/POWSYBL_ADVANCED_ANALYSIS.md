# PowSyBl 高度分析アプリケーション設計書

## 概要

PowSyBlライブラリを活用した変電所デジタルツイン向けの高度な電力系統分析・シミュレーションアプリケーション。

## システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    IT Zone (Visualization)                   │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │   Grafana    │◄───│  Analysis Results Dashboard       │  │
│  └──────────────┘    └──────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│                    App Zone (Analysis Engine)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        PowSyBl Advanced Analysis Service             │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  FastAPI REST API                              │  │   │
│  │  │  - /loadflow       (潮流計算)                   │  │   │
│  │  │  - /security       (セキュリティ分析)            │  │   │
│  │  │  - /sensitivity    (感度分析)                   │  │   │
│  │  │  - /optimal        (最適潮流)                   │  │   │
│  │  │  - /dynamic        (動的シミュレーション)         │  │   │
│  │  │  - /shortcircuit   (短絡分析)                   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  PyPowSyBl Analysis Core                       │  │   │
│  │  │  - Network Model Manager                       │  │   │
│  │  │  - Load Flow Engine                            │  │   │
│  │  │  - Security Analysis Engine                    │  │   │
│  │  │  - Sensitivity Analysis Engine                 │  │   │
│  │  │  - Optimization Engine                         │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│                    Data Zone (Data Storage)                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   InfluxDB   │    │    Redis     │    │  PostgreSQL  │  │
│  │  (Telemetry) │    │  (Real-time) │    │  (Results)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 主要機能

### 1. Load Flow Analysis (潮流計算)
**目的**: 定常状態における電力系統の電圧、位相角、潮流を計算

**機能**:
- AC Load Flow (Newton-Raphson法)
- DC Load Flow (線形近似)
- 電圧プロファイル計算
- 有効・無効電力フロー計算
- 損失計算

**入力**:
- ネットワークモデル（IIDM形式）
- 発電機出力
- 負荷データ
- 計算パラメータ

**出力**:
- バス電圧・位相角
- ブランチ潮流
- 発電機出力
- 損失
- 収束状態

### 2. Security Analysis (セキュリティ分析)
**目的**: N-1/N-K基準でのシステム安定性評価

**機能**:
- N-1分析（単一機器故障）
- N-K分析（複数機器故障）
- コンティンジェンシー評価
- 制約違反検出
- 予防・是正措置の効果評価

**コンティンジェンシータイプ**:
- 発電機脱落
- 送電線・変圧器開放
- バス停止
- HVDC線停止

**出力**:
- 違反リスト（電圧、電流、角度）
- 各コンティンジェンシーの影響
- 是正措置の提案

### 3. Sensitivity Analysis (感度分析)
**目的**: システムパラメータ変化の影響を評価

**機能**:
- PTDF (Power Transfer Distribution Factor)
- PSDF (Phase Shift Distribution Factor)
- DCDF (DC Distribution Factor)
- 電圧感度分析
- ゾーン間潮流感度

**用途**:
- 発電機出力変化の影響評価
- 負荷変化の影響評価
- 位相調整器の効果評価
- HVDC制御の影響評価

### 4. Optimal Power Flow (最適潮流)
**目的**: 制約条件下での運用コスト最小化

**最適化目標**:
- 発電コスト最小化
- 損失最小化
- 電圧プロファイル最適化
- 再生可能エネルギー最大活用

**制約条件**:
- 電力バランス
- 電圧制約
- 送電容量制約
- 発電機出力制約

### 5. Dynamic Simulation (動的シミュレーション)
**目的**: 過渡現象・動的挙動の時間領域シミュレーション

**機能**:
- 発電機動特性シミュレーション
- 系統安定性評価
- 故障応答シミュレーション
- 周波数・電圧動特性

**用途**:
- 系統安定度評価
- 保護協調検証
- 再生可能エネルギー統合影響評価

### 6. Short-Circuit Analysis (短絡分析)
**目的**: 短絡故障時の電流計算

**機能**:
- 3相短絡電流計算
- 相間短絡電流計算
- 地絡電流計算
- 遮断器定格検証

## データモデル

### ネットワークモデル (IIDM)
```
Network
├── Substations
│   ├── Voltage Levels
│   │   ├── Buses
│   │   ├── Generators
│   │   ├── Loads
│   │   └── Shunt Compensators
│   └── Transformers
└── Lines
    ├── AC Lines
    └── HVDC Lines
```

### 分析結果データモデル

#### Load Flow Results
```python
{
  "timestamp": "ISO-8601",
  "convergence_status": "CONVERGED|PARTIALLY_CONVERGED|FAILED",
  "iterations": int,
  "buses": [
    {
      "id": str,
      "voltage_magnitude": float,  # kV
      "voltage_angle": float,      # degrees
      "active_power": float,       # MW
      "reactive_power": float      # MVAr
    }
  ],
  "branches": [
    {
      "id": str,
      "active_power_from": float,
      "reactive_power_from": float,
      "active_power_to": float,
      "reactive_power_to": float,
      "current": float,
      "loading": float  # %
    }
  ],
  "losses": {
    "active_power": float,
    "reactive_power": float
  }
}
```

#### Security Analysis Results
```python
{
  "timestamp": "ISO-8601",
  "base_case": {
    "violations": [...]
  },
  "contingencies": [
    {
      "id": str,
      "elements": [str],
      "status": "CONVERGED|FAILED",
      "violations": [
        {
          "subject_id": str,
          "type": "CURRENT|VOLTAGE|ANGLE",
          "limit": float,
          "value": float,
          "side": "ONE|TWO"
        }
      ]
    }
  ],
  "summary": {
    "total_contingencies": int,
    "failed_contingencies": int,
    "critical_violations": int
  }
}
```

#### Sensitivity Analysis Results
```python
{
  "timestamp": "ISO-8601",
  "factors": [
    {
      "function_id": str,      # 監視対象（ブランチID等）
      "function_type": "BRANCH_ACTIVE_POWER|BUS_VOLTAGE",
      "variable_id": str,      # 変数（発電機ID等）
      "variable_type": "INJECTION_ACTIVE_POWER|TRANSFORMER_PHASE",
      "value": float,          # 感度係数
      "reference_value": float
    }
  ]
}
```

## API エンドポイント

### Load Flow
```
POST /api/v1/loadflow
Content-Type: application/json

{
  "network_id": str,
  "parameters": {
    "voltage_init_mode": "UNIFORM_VALUES|PREVIOUS_VALUES",
    "transformer_voltage_control_on": bool,
    "phase_shifter_regulation_on": bool,
    "dc": bool
  }
}

Response: LoadFlowResult
```

### Security Analysis
```
POST /api/v1/security
Content-Type: application/json

{
  "network_id": str,
  "contingencies": [
    {
      "id": str,
      "elements": [str]
    }
  ],
  "parameters": {
    "load_flow_parameters": {...}
  }
}

Response: SecurityAnalysisResult
```

### Sensitivity Analysis
```
POST /api/v1/sensitivity
Content-Type: application/json

{
  "network_id": str,
  "factors": [
    {
      "function_type": "BRANCH_ACTIVE_POWER",
      "function_id": str,
      "variable_type": "INJECTION_ACTIVE_POWER",
      "variable_id": str,
      "variable_set": bool
    }
  ],
  "parameters": {
    "analysis_type": "DC|AC"
  }
}

Response: SensitivityAnalysisResult
```

### Optimal Power Flow
```
POST /api/v1/optimal
Content-Type: application/json

{
  "network_id": str,
  "objective": {
    "type": "MIN_GENERATION_COST|MIN_LOSSES",
    "generators_costs": {
      "gen_id": {"a": float, "b": float, "c": float}
    }
  },
  "constraints": {
    "voltage_limits": bool,
    "thermal_limits": bool,
    "generator_limits": bool
  }
}

Response: OptimalPowerFlowResult
```

## 統合フロー

### リアルタイム分析フロー
```
IED → FledgePOWER → Redis → Network State Builder
                                    ↓
                            PyPowSyBl Network Model
                                    ↓
        ┌───────────────────────────┼───────────────────────────┐
        ↓                           ↓                           ↓
   Load Flow                Security Analysis         Sensitivity Analysis
        ↓                           ↓                           ↓
    InfluxDB ←──────────────────────┴───────────────────────────┘
        ↓
    Grafana Dashboard
```

### バッチ分析フロー
```
Scheduled Job → Network Snapshot → Analysis Engine
                                         ↓
                                   Results Storage
                                         ↓
                                   Report Generation
```

## デプロイメント構成

### コンテナ構成
```
powsybl-analysis-engine/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py
│   ├── models/
│   │   ├── network.py
│   │   ├── loadflow.py
│   │   ├── security.py
│   │   └── sensitivity.py
│   ├── services/
│   │   ├── network_service.py
│   │   ├── loadflow_service.py
│   │   ├── security_service.py
│   │   ├── sensitivity_service.py
│   │   └── optimal_service.py
│   └── api/
│       └── v1/
│           ├── loadflow.py
│           ├── security.py
│           ├── sensitivity.py
│           └── optimal.py
└── tests/
```

### リソース要件
- CPU: 4-8 cores (計算集約的)
- Memory: 8-16 GB (大規模ネットワーク用)
- Storage: 20 GB

## パフォーマンス目標

- Load Flow計算: < 5秒 (1000ノードネットワーク)
- Security Analysis (N-1): < 30秒 (100コンティンジェンシー)
- Sensitivity Analysis: < 10秒 (1000ファクター)
- リアルタイム分析更新頻度: 5秒

## セキュリティ考慮事項

- API認証・認可
- ネットワークモデルのアクセス制御
- 分析結果の暗号化
- 監査ログ

## 今後の拡張

1. 機械学習による異常検知
2. 予測的メンテナンス
3. 市場分析統合
4. マルチタイムスケール最適化
5. 分散エネルギー資源（DER）統合
