"""
Sensitivity Analysis Service
感度分析サービス
"""
import pypowsybl as pp
import pypowsybl.sensitivity as sensitivity
from typing import List, Dict
from datetime import datetime
import time
import logging
from ..models.sensitivity import (
    SensitivityAnalysisRequest,
    SensitivityAnalysisResult,
    SensitivityFactor,
    SensitivityValue,
    FunctionType,
    VariableType
)
from .network_service import NetworkService

logger = logging.getLogger(__name__)


class SensitivityService:
    """感度分析サービス"""

    def __init__(self, network_service: NetworkService):
        self.network_service = network_service

    def run_sensitivity_analysis(self, request: SensitivityAnalysisRequest) -> SensitivityAnalysisResult:
        """
        感度分析を実行
        PTDF, PSDF, DCDF等を計算
        """
        start_time = time.time()

        try:
            # ネットワーク取得
            network = self.network_service.get_network(request.network_id)
            if not network:
                raise ValueError(f"Network not found: {request.network_id}")

            # 感度係数マトリクス構築
            factors_matrix = self._build_sensitivity_matrix(request.factors)

            # 分析タイプ（DC or AC）
            analysis_type = request.parameters.get("analysis_type", "DC")

            logger.info(f"Running {analysis_type} sensitivity analysis for network: {request.network_id}, "
                       f"factors: {len(request.factors)}")

            # 感度分析実行
            if analysis_type == "DC":
                analysis = sensitivity.create_dc_analysis()
            else:
                analysis = sensitivity.create_ac_analysis()

            results = analysis.run(network, factors_matrix)

            # 結果の解析
            sensitivity_values = self._extract_sensitivity_values(request.factors, results)
            matrix_data = self._build_matrix_representation(sensitivity_values)

            computation_time = (time.time() - start_time) * 1000  # ms

            return SensitivityAnalysisResult(
                timestamp=datetime.utcnow().isoformat() + "Z",
                network_id=request.network_id,
                factors=sensitivity_values,
                computation_time_ms=computation_time,
                matrix=matrix_data
            )

        except Exception as e:
            logger.error(f"Sensitivity analysis failed: {e}")
            raise

    def _build_sensitivity_matrix(self, factors: List[SensitivityFactor]):
        """感度係数マトリクスを構築"""
        matrix = []
        for factor in factors:
            matrix.append({
                "function_type": self._map_function_type(factor.function_type),
                "function_id": factor.function_id,
                "variable_type": self._map_variable_type(factor.variable_type),
                "variable_id": factor.variable_id,
                "variable_set": factor.variable_set
            })
        return matrix

    def _map_function_type(self, func_type: FunctionType) -> str:
        """関数タイプをPyPowSyBl形式にマッピング"""
        mapping = {
            FunctionType.BRANCH_ACTIVE_POWER: "BRANCH_ACTIVE_POWER_1",
            FunctionType.BRANCH_REACTIVE_POWER: "BRANCH_REACTIVE_POWER_1",
            FunctionType.BRANCH_CURRENT: "BRANCH_CURRENT_1",
            FunctionType.BUS_VOLTAGE: "BUS_VOLTAGE"
        }
        return mapping.get(func_type, "BRANCH_ACTIVE_POWER_1")

    def _map_variable_type(self, var_type: VariableType) -> str:
        """変数タイプをPyPowSyBl形式にマッピング"""
        mapping = {
            VariableType.INJECTION_ACTIVE_POWER: "INJECTION_ACTIVE_POWER",
            VariableType.INJECTION_REACTIVE_POWER: "INJECTION_REACTIVE_POWER",
            VariableType.TRANSFORMER_PHASE: "TRANSFORMER_PHASE",
            VariableType.BUS_TARGET_VOLTAGE: "BUS_TARGET_VOLTAGE",
            VariableType.HVDC_LINE_ACTIVE_POWER: "HVDC_LINE_ACTIVE_POWER"
        }
        return mapping.get(var_type, "INJECTION_ACTIVE_POWER")

    def _extract_sensitivity_values(
        self,
        factors: List[SensitivityFactor],
        results
    ) -> List[SensitivityValue]:
        """感度値を抽出"""
        sensitivity_values = []

        # 結果からデータフレームを取得
        if hasattr(results, 'to_frame'):
            df = results.to_frame()

            for idx, row in df.iterrows():
                # 対応するファクター定義を検索
                for factor in factors:
                    if (row['function_id'] == factor.function_id and
                        row['variable_id'] == factor.variable_id):

                        sensitivity_values.append(SensitivityValue(
                            function_id=row['function_id'],
                            function_type=factor.function_type,
                            variable_id=row['variable_id'],
                            variable_type=factor.variable_type,
                            value=row.get('value', 0.0),
                            reference_value=row.get('reference_value', 0.0)
                        ))
                        break

        return sensitivity_values

    def _build_matrix_representation(
        self,
        sensitivity_values: List[SensitivityValue]
    ) -> Dict[str, Dict[str, float]]:
        """
        感度係数をマトリクス形式に変換
        matrix[function_id][variable_id] = sensitivity_value
        """
        matrix = {}

        for sv in sensitivity_values:
            if sv.function_id not in matrix:
                matrix[sv.function_id] = {}

            matrix[sv.function_id][sv.variable_id] = sv.value

        return matrix

    def generate_ptdf_factors(
        self,
        network_id: str,
        monitored_branches: List[str],
        injection_points: List[str]
    ) -> List[SensitivityFactor]:
        """
        PTDF (Power Transfer Distribution Factor) 用の感度係数を自動生成
        """
        factors = []

        for branch_id in monitored_branches:
            for injection_id in injection_points:
                factors.append(SensitivityFactor(
                    function_type=FunctionType.BRANCH_ACTIVE_POWER,
                    function_id=branch_id,
                    variable_type=VariableType.INJECTION_ACTIVE_POWER,
                    variable_id=injection_id,
                    variable_set=False
                ))

        logger.info(f"Generated {len(factors)} PTDF factors")
        return factors

    def generate_voltage_sensitivity_factors(
        self,
        network_id: str,
        monitored_buses: List[str],
        control_generators: List[str]
    ) -> List[SensitivityFactor]:
        """電圧感度用の感度係数を自動生成"""
        factors = []

        for bus_id in monitored_buses:
            for gen_id in control_generators:
                # 無効電力による電圧感度
                factors.append(SensitivityFactor(
                    function_type=FunctionType.BUS_VOLTAGE,
                    function_id=bus_id,
                    variable_type=VariableType.INJECTION_REACTIVE_POWER,
                    variable_id=gen_id,
                    variable_set=False
                ))

        logger.info(f"Generated {len(factors)} voltage sensitivity factors")
        return factors
