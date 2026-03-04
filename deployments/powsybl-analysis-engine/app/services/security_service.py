"""
Security Analysis Service
セキュリティ分析サービス
"""
import pypowsybl as pp
import pypowsybl.security as security
from typing import List
from datetime import datetime
import time
import logging
from ..models.security import (
    SecurityAnalysisRequest,
    SecurityAnalysisResult,
    Contingency,
    ContingencyResult,
    Violation,
    ViolationType,
    LimitSide
)
from .network_service import NetworkService

logger = logging.getLogger(__name__)


class SecurityService:
    """セキュリティ分析サービス"""

    def __init__(self, network_service: NetworkService):
        self.network_service = network_service

    def run_security_analysis(self, request: SecurityAnalysisRequest) -> SecurityAnalysisResult:
        """
        セキュリティ分析を実行（N-1/N-K分析）
        """
        start_time = time.time()

        try:
            # ネットワーク取得
            network = self.network_service.get_network(request.network_id)
            if not network:
                raise ValueError(f"Network not found: {request.network_id}")

            # コンティンジェンシーリスト構築
            contingencies = self._build_contingencies(request.contingencies)

            # セキュリティ分析実行
            logger.info(f"Running security analysis for network: {request.network_id}, "
                       f"contingencies: {len(contingencies)}")

            results = security.run_security_analysis(
                network=network,
                contingencies=contingencies,
                parameters=request.parameters or {}
            )

            # 結果の解析
            base_case_violations = self._extract_violations(results.pre_contingency_result)
            contingency_results = self._extract_contingency_results(results)

            # サマリー計算
            summary = self._calculate_summary(contingency_results)

            computation_time = (time.time() - start_time) * 1000  # ms

            return SecurityAnalysisResult(
                timestamp=datetime.utcnow().isoformat() + "Z",
                network_id=request.network_id,
                base_case={"violations": base_case_violations},
                contingencies=contingency_results,
                summary=summary,
                computation_time_ms=computation_time
            )

        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
            raise

    def _build_contingencies(self, contingency_defs: List[Contingency]):
        """コンティンジェンシーリストを構築"""
        contingencies = []
        for cont_def in contingency_defs:
            # PyPowSyBl用のコンティンジェンシーオブジェクトを作成
            elements = []
            for element_id in cont_def.elements:
                elements.append(pp.contingency.create_branch_contingency(element_id))

            contingencies.append(
                pp.contingency.create_contingency(cont_def.id, elements)
            )

        return contingencies

    def _extract_violations(self, result) -> List[Violation]:
        """制約違反を抽出"""
        violations = []

        if not result:
            return violations

        # 電流制約違反
        for violation in result.limit_violations:
            violations.append(Violation(
                subject_id=violation.subject_id,
                violation_type=self._map_violation_type(violation.limit_type),
                limit=violation.limit,
                value=violation.value,
                side=LimitSide.ONE if violation.side == "ONE" else LimitSide.TWO,
                acceptable_duration=violation.acceptable_duration
            ))

        return violations

    def _map_violation_type(self, limit_type: str) -> ViolationType:
        """制約タイプをマッピング"""
        mapping = {
            "CURRENT": ViolationType.CURRENT,
            "LOW_VOLTAGE": ViolationType.VOLTAGE,
            "HIGH_VOLTAGE": ViolationType.VOLTAGE,
            "ACTIVE_POWER": ViolationType.ACTIVE_POWER,
            "APPARENT_POWER": ViolationType.CURRENT
        }
        return mapping.get(limit_type, ViolationType.CURRENT)

    def _extract_contingency_results(self, results) -> List[ContingencyResult]:
        """コンティンジェンシー結果を抽出"""
        contingency_results = []

        for post_result in results.post_contingency_results:
            violations = self._extract_violations(post_result)

            contingency_results.append(ContingencyResult(
                id=post_result.contingency_id,
                elements=[],  # 元の定義から取得
                status=post_result.status,
                violations=violations,
                limit_violations_count=len(violations)
            ))

        return contingency_results

    def _calculate_summary(self, contingency_results: List[ContingencyResult]) -> dict:
        """サマリー情報を計算"""
        total = len(contingency_results)
        failed = sum(1 for r in contingency_results if r.status != "CONVERGED")
        critical = sum(1 for r in contingency_results if len(r.violations) > 0)

        return {
            "total_contingencies": total,
            "failed_contingencies": failed,
            "critical_violations": critical
        }

    def generate_n1_contingencies(self, network_id: str) -> List[Contingency]:
        """
        N-1コンティンジェンシーを自動生成
        全ての送電線と変圧器に対する単一故障
        """
        network = self.network_service.get_network(network_id)
        if not network:
            raise ValueError(f"Network not found: {network_id}")

        contingencies = []

        # 送電線
        lines = network.get_lines()
        for line_id in lines.index:
            contingencies.append(Contingency(
                id=f"N1_LINE_{line_id}",
                elements=[line_id]
            ))

        # 変圧器
        transformers = network.get_2_windings_transformers()
        for xfmr_id in transformers.index:
            contingencies.append(Contingency(
                id=f"N1_XFMR_{xfmr_id}",
                elements=[xfmr_id]
            ))

        logger.info(f"Generated {len(contingencies)} N-1 contingencies")
        return contingencies
