"""
Sensitivity Analysis Models
感度分析モデル
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class FunctionType(str, Enum):
    """関数タイプ"""
    BRANCH_ACTIVE_POWER = "BRANCH_ACTIVE_POWER"
    BRANCH_REACTIVE_POWER = "BRANCH_REACTIVE_POWER"
    BRANCH_CURRENT = "BRANCH_CURRENT"
    BUS_VOLTAGE = "BUS_VOLTAGE"


class VariableType(str, Enum):
    """変数タイプ"""
    INJECTION_ACTIVE_POWER = "INJECTION_ACTIVE_POWER"
    INJECTION_REACTIVE_POWER = "INJECTION_REACTIVE_POWER"
    TRANSFORMER_PHASE = "TRANSFORMER_PHASE"
    BUS_TARGET_VOLTAGE = "BUS_TARGET_VOLTAGE"
    HVDC_LINE_ACTIVE_POWER = "HVDC_LINE_ACTIVE_POWER"


class SensitivityFactor(BaseModel):
    """感度係数定義"""
    function_type: FunctionType
    function_id: str = Field(..., description="監視対象ID")
    variable_type: VariableType
    variable_id: str = Field(..., description="変数ID")
    variable_set: bool = False


class SensitivityAnalysisRequest(BaseModel):
    """感度分析リクエスト"""
    network_id: str
    factors: List[SensitivityFactor]
    parameters: Optional[Dict] = Field(
        default_factory=lambda: {"analysis_type": "DC"}
    )


class SensitivityValue(BaseModel):
    """感度値"""
    function_id: str
    function_type: FunctionType
    variable_id: str
    variable_type: VariableType
    value: float = Field(..., description="感度係数")
    reference_value: float = Field(..., description="基準値")


class SensitivityAnalysisResult(BaseModel):
    """感度分析結果"""
    timestamp: str
    network_id: str
    factors: List[SensitivityValue]
    computation_time_ms: float

    # PTDF, PSDF等のマトリクス表現用
    matrix: Optional[Dict[str, Dict[str, float]]] = None
