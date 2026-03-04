"""
Load Flow Analysis Service
潮流計算サービス
"""
import pypowsybl as pp
import pypowsybl.loadflow as lf
from typing import Dict, Any
from datetime import datetime
import time
import logging
from ..models.loadflow import (
    LoadFlowRequest,
    LoadFlowResult,
    LoadFlowParameters,
    ConvergenceStatus,
    BusData,
    BranchData,
    LossesData
)
from .network_service import NetworkService

logger = logging.getLogger(__name__)


class LoadFlowService:
    """潮流計算サービス"""

    def __init__(self, network_service: NetworkService):
        self.network_service = network_service

    def run_loadflow(self, request: LoadFlowRequest) -> LoadFlowResult:
        """
        潮流計算を実行
        """
        start_time = time.time()

        try:
            # ネットワーク取得
            network = self.network_service.get_network(request.network_id)
            if not network:
                raise ValueError(f"Network not found: {request.network_id}")

            # パラメータ設定
            params = self._build_parameters(request.parameters)

            # 潮流計算実行
            logger.info(f"Running load flow for network: {request.network_id}")
            results = lf.run_ac(network, params) if not request.parameters.dc else lf.run_dc(network, params)

            # 結果の解析
            convergence_status = self._determine_convergence_status(results)
            buses_data = self._extract_bus_data(network)
            branches_data = self._extract_branch_data(network)
            losses = self._calculate_losses(branches_data)

            computation_time = (time.time() - start_time) * 1000  # ms

            return LoadFlowResult(
                timestamp=datetime.utcnow().isoformat() + "Z",
                network_id=request.network_id,
                convergence_status=convergence_status,
                iterations=results[0].iteration_count if results else 0,
                buses=buses_data,
                branches=branches_data,
                losses=losses,
                computation_time_ms=computation_time,
                metrics={
                    "slack_bus_active_power_mismatch": results[0].slack_bus_active_power_mismatch if results else 0
                }
            )

        except Exception as e:
            logger.error(f"Load flow calculation failed: {e}")
            raise

    def _build_parameters(self, params: LoadFlowParameters) -> Dict[str, Any]:
        """PyPowSyBl用のパラメータを構築"""
        return {
            "voltage_init_mode": params.voltage_init_mode,
            "transformer_voltage_control_on": params.transformer_voltage_control_on,
            "phase_shifter_regulation_on": params.phase_shifter_regulation_on,
            "distributed_slack": params.distributed_slack,
            "balance_type": params.balance_type
        }

    def _determine_convergence_status(self, results) -> ConvergenceStatus:
        """収束状態を判定"""
        if not results:
            return ConvergenceStatus.FAILED

        all_converged = all(r.status == "CONVERGED" for r in results)
        any_converged = any(r.status == "CONVERGED" for r in results)

        if all_converged:
            return ConvergenceStatus.CONVERGED
        elif any_converged:
            return ConvergenceStatus.PARTIALLY_CONVERGED
        else:
            return ConvergenceStatus.FAILED

    def _extract_bus_data(self, network) -> list[BusData]:
        """バスデータを抽出"""
        buses = []
        bus_df = network.get_buses()

        for idx, bus in bus_df.iterrows():
            buses.append(BusData(
                id=bus['name'],
                voltage_magnitude=bus.get('v_mag', 0.0),
                voltage_angle=bus.get('v_angle', 0.0),
                active_power=0.0,  # 計算が必要
                reactive_power=0.0
            ))

        return buses

    def _extract_branch_data(self, network) -> list[BranchData]:
        """ブランチ（送電線・変圧器）データを抽出"""
        branches = []

        # 送電線
        lines_df = network.get_lines()
        for idx, line in lines_df.iterrows():
            branches.append(BranchData(
                id=line['name'],
                active_power_from=line.get('p1', 0.0),
                reactive_power_from=line.get('q1', 0.0),
                active_power_to=line.get('p2', 0.0),
                reactive_power_to=line.get('q2', 0.0),
                current=line.get('i1', 0.0),
                loading=self._calculate_loading(line)
            ))

        # 変圧器
        transformers_df = network.get_2_windings_transformers()
        for idx, xfmr in transformers_df.iterrows():
            branches.append(BranchData(
                id=xfmr['name'],
                active_power_from=xfmr.get('p1', 0.0),
                reactive_power_from=xfmr.get('q1', 0.0),
                active_power_to=xfmr.get('p2', 0.0),
                reactive_power_to=xfmr.get('q2', 0.0),
                current=xfmr.get('i1', 0.0),
                loading=self._calculate_loading(xfmr)
            ))

        return branches

    def _calculate_loading(self, element) -> float:
        """負荷率を計算"""
        current = element.get('i1', 0.0)
        # 定格電流は機器定義から取得する必要がある（ここでは仮実装）
        rated_current = 1000.0
        return (current / rated_current * 100.0) if rated_current > 0 else 0.0

    def _calculate_losses(self, branches: list[BranchData]) -> LossesData:
        """系統全体の損失を計算"""
        total_active_loss = 0.0
        total_reactive_loss = 0.0

        for branch in branches:
            # 損失 = 送端 - 受端（符号を考慮）
            active_loss = branch.active_power_from + branch.active_power_to
            reactive_loss = branch.reactive_power_from + branch.reactive_power_to

            total_active_loss += abs(active_loss)
            total_reactive_loss += abs(reactive_loss)

        return LossesData(
            active_power=total_active_loss,
            reactive_power=total_reactive_loss
        )
