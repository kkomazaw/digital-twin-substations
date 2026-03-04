"""
Network Models for PowSyBl Analysis Engine
ネットワークモデルの定義
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class VoltageInitMode(str, Enum):
    """電圧初期化モード"""
    UNIFORM_VALUES = "UNIFORM_VALUES"
    PREVIOUS_VALUES = "PREVIOUS_VALUES"
    DC_VALUES = "DC_VALUES"


class BusData(BaseModel):
    """バスデータ"""
    id: str
    voltage_magnitude: float = Field(..., description="電圧振幅 (kV)")
    voltage_angle: float = Field(..., description="電圧位相角 (degrees)")
    active_power: float = Field(..., description="有効電力 (MW)")
    reactive_power: float = Field(..., description="無効電力 (MVAr)")


class BranchData(BaseModel):
    """ブランチデータ（送電線・変圧器）"""
    id: str
    active_power_from: float = Field(..., description="送端有効電力 (MW)")
    reactive_power_from: float = Field(..., description="送端無効電力 (MVAr)")
    active_power_to: float = Field(..., description="受端有効電力 (MW)")
    reactive_power_to: float = Field(..., description="受端無効電力 (MVAr)")
    current: float = Field(..., description="電流 (A)")
    loading: float = Field(..., description="負荷率 (%)")


class GeneratorData(BaseModel):
    """発電機データ"""
    id: str
    target_p: float = Field(..., description="目標有効電力 (MW)")
    target_v: float = Field(..., description="目標電圧 (kV)")
    min_p: float = Field(..., description="最小有効電力 (MW)")
    max_p: float = Field(..., description="最大有効電力 (MW)")
    voltage_regulator_on: bool = True


class LoadData(BaseModel):
    """負荷データ"""
    id: str
    p0: float = Field(..., description="有効電力 (MW)")
    q0: float = Field(..., description="無効電力 (MVAr)")


class NetworkSnapshot(BaseModel):
    """ネットワークスナップショット"""
    network_id: str
    timestamp: str
    buses: List[BusData]
    branches: List[BranchData]
    generators: List[GeneratorData]
    loads: List[LoadData]
    metadata: Optional[Dict[str, Any]] = None
