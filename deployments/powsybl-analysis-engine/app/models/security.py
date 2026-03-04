"""
Security Analysis Models
セキュリティ分析モデル
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class ViolationType(str, Enum):
    """違反タイプ"""
    CURRENT = "CURRENT"
    VOLTAGE = "VOLTAGE"
    ANGLE = "ANGLE"
    ACTIVE_POWER = "ACTIVE_POWER"


class LimitSide(str, Enum):
    """制限側"""
    ONE = "ONE"
    TWO = "TWO"
    BOTH = "BOTH"


class Violation(BaseModel):
    """制約違反"""
    subject_id: str = Field(..., description="対象機器ID")
    violation_type: ViolationType
    limit: float = Field(..., description="制限値")
    value: float = Field(..., description="実際の値")
    side: Optional[LimitSide] = None
    acceptable_duration: Optional[int] = Field(None, description="許容時間 (秒)")


class Contingency(BaseModel):
    """コンティンジェンシー定義"""
    id: str
    elements: List[str] = Field(..., description="故障対象機器IDリスト")


class ContingencyResult(BaseModel):
    """コンティンジェンシー結果"""
    id: str
    elements: List[str]
    status: str = Field(..., description="CONVERGED|FAILED")
    violations: List[Violation]
    limit_violations_count: int = 0


class SecurityAnalysisRequest(BaseModel):
    """セキュリティ分析リクエスト"""
    network_id: str
    contingencies: List[Contingency]
    parameters: Optional[Dict] = None


class SecurityAnalysisResult(BaseModel):
    """セキュリティ分析結果"""
    timestamp: str
    network_id: str
    base_case: Dict[str, List[Violation]] = Field(default_factory=lambda: {"violations": []})
    contingencies: List[ContingencyResult]
    summary: Dict[str, int] = Field(
        default_factory=lambda: {
            "total_contingencies": 0,
            "failed_contingencies": 0,
            "critical_violations": 0
        }
    )
    computation_time_ms: float
