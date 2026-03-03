では、送配電会社向けデジタル変電所基盤の詳細ネットワークトポロジ設計を
IEC 62443ゾーニングを前提に作成します。

目的：

OT/IT分離

ゼロトラスト適用

多拠点（複数変電所）接続

中央解析基盤との安全連携

🏗 全体ネットワークトポロジ（論理構成）
                               ┌─────────────────────────────┐
                               │        中央データセンター     │
                               │                             │
                               │  ┌───────────────────────┐  │
                               │  │  IT Zone              │  │
                               │  │  - UI (Grafana)       │  │
                               │  │  - API Gateway        │  │
                               │  │  - Auth (Keycloak)    │  │
                               │  └─────────────┬─────────┘  │
                               │                │ mTLS        │
                               │  ┌─────────────▼─────────┐  │
                               │  │  Application Zone     │  │
                               │  │  - PowSyBl API        │  │
                               │  │  - AI Services        │  │
                               │  │  - Model Services     │  │
                               │  └─────────────┬─────────┘  │
                               │                │             │
                               │  ┌─────────────▼─────────┐  │
                               │  │  Data Zone           │  │
                               │  │  - Kafka Cluster     │  │
                               │  │  - Postgres          │  │
                               │  │  - InfluxDB          │  │
                               │  └───────────────────────┘  │
                               └───────────────▲─────────────┘
                                               │ IPSec VPN / MPLS
───────────────────────────────────────────────┼──────────────────────────
                                               │
                     ┌─────────────────────────┴─────────────────────────┐
                     │                   変電所 A                         │
                     │                                                     │
                     │  ┌───────────────────────────────┐                  │
                     │  │      OT Zone (Level 0-2)      │                  │
                     │  │  - IED                         │                  │
                     │  │  - Protection Relay            │                  │
                     │  │  - Merging Unit (SV)           │                  │
                     │  └───────────────┬────────────────┘                  │
                     │                  │ IEC 61850                          │
                     │  ┌───────────────▼────────────────┐                  │
                     │  │     Station Bus (Layer2 VLAN)  │                  │
                     │  └───────────────┬────────────────┘                  │
                     │                  │                                    │
                     │  ┌───────────────▼────────────────┐                  │
                     │  │      DMZ / Edge Zone           │                  │
                     │  │  - Fledge Server               │                  │
                     │  │  - Local Kafka (optional)      │                  │
                     │  │  - Firewall                    │                  │
                     │  └───────────────┬────────────────┘                  │
                     │                  │                                    │
                     │  ┌───────────────▼────────────────┐                  │
                     │  │  WAN Router + IPSec Gateway    │                  │
                     │  └─────────────────────────────────┘                  │
                     └───────────────────────────────────────────────────────┘
🔐 ゾーニング設計（IEC 62443準拠）
OT Zone（Level 0-2）

IED

保護装置

Merging Unit

GOOSE / SV通信

🔒 外部直接接続禁止
🔒 L2 VLAN分離
🔒 MAC制御

Station Bus

IEC 61850専用VLAN

PRP/HSR冗長化

L2限定

DMZ / Edge Zone（Level 3）

Fledge

ローカルバッファ

Firewall

役割：

OTデータ吸収

プロトコル変換

上位送信のみ許可

WAN接続

MPLS or 専用線

IPSec VPN

双方向通信は制限

中央DC内部ゾーン
IT Zone

外部アクセス

API Gateway

SSO

Application Zone

解析サービス

AI

Data Zone

DB群

Kafka

🔒 NetworkPolicy適用
🔒 east-west mTLS

🌐 VLAN分離例（変電所内）
VLAN	用途
VLAN10	Process Bus (SV)
VLAN20	Station Bus (MMS/GOOSE)
VLAN30	Engineering Access
VLAN40	Edge/Fledge
VLAN50	管理用
🔄 データフロー制御

IED → Fledge（内部）

Fledge → DMZ Firewall

DMZ → VPN

VPN → 中央Kafka

Kafka → 解析

外部からOTへ直接接続禁止

🛡 セキュリティ対策詳細
1. Firewallルール

OT → Edge：許可

Edge → Central：許可

Central → OT：原則禁止

2. 認証

Fledge → Kafka：mTLS

UI → API：OIDC

3. IDS/IPS

OTネットワーク監視

異常通信検出

🏢 大規模導入（200変電所）時

トポロジは：

各変電所 → 集約リージョンDC

リージョンDC → 中央DC

解析は中央集中

🔄 冗長構成
変電所

Fledge 2台構成（Active/Standby）

中央

Kafka 3-5 Broker

DBレプリケーション

Multi-AZ

📊 トラフィック試算（例）

1変電所：

1秒周期 × 200点

約 5〜10 Mbps

200変電所：

約 1〜2 Gbps

→ 圧縮・集約必須

🎯 設計思想

✔ OT完全保護
✔ DMZ吸収
✔ 双方向制御最小化
✔ 中央解析集中
✔ 将来クラウド移行可能

