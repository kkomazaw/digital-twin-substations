"""
Load Flow Analysis Models
潮流計算モデル
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from .network import BusData, BranchData


class ConvergenceStatus(str, Enum):
    """収束状態"""
    CONVERGED = "CONVERGED"
    PARTIALLY_CONVERGED = "PARTIALLY_CONVERGED"
    FAILED = "FAILED"


class LoadFlowParameters(BaseModel):
    """潮流計算パラメータ"""
    voltage_init_mode: str = "UNIFORM_VALUES"
    transformer_voltage_control_on: bool = True
    phase_shifter_regulation_on: bool = True
    dc: bool = False  # DC潮流計算フラグ
    distributed_slack: bool = True
    balance_type: str = "PROPORTIONAL_TO_GENERATION_P_MAX"
    max_iterations: int = 100
    tolerance: float = 1e-4


class LoadFlowRequest(BaseModel):
    """潮流計算リクエスト"""
    network_id: str
    parameters: Optional[LoadFlowParameters] = LoadFlowParameters()


class LossesData(BaseModel):
    """損失データ"""
    active_power: float = Field(..., description="有効電力損失 (MW)")
    reactive_power: float = Field(..., description="無効電力損失 (MVAr)")


class LoadFlowResult(BaseModel):
    """潮流計算結果"""
    timestamp: str
    network_id: str
    convergence_status: ConvergenceStatus
    iterations: int
    buses: List[BusData]
    branches: List[BranchData]
    losses: LossesData
    computation_time_ms: float
    metrics: Optional[Dict[str, float]] = None
