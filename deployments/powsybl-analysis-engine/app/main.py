"""
PowSyBl Advanced Analysis Engine
電力系統高度分析エンジン - メインアプリケーション
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Services
from .services import (
    NetworkService,
    LoadFlowService,
    SecurityService,
    SensitivityService
)

# Models
from .models.loadflow import LoadFlowRequest, LoadFlowResult
from .models.security import SecurityAnalysisRequest, SecurityAnalysisResult
from .models.sensitivity import SensitivityAnalysisRequest, SensitivityAnalysisResult

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# サービスインスタンス（グローバル）
network_service = None
loadflow_service = None
security_service = None
sensitivity_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    global network_service, loadflow_service, security_service, sensitivity_service

    # 起動時の初期化
    logger.info("Starting PowSyBl Advanced Analysis Engine...")

    network_service = NetworkService()
    loadflow_service = LoadFlowService(network_service)
    security_service = SecurityService(network_service)
    sensitivity_service = SensitivityService(network_service)

    # サンプルネットワークの作成（デモ用）
    try:
        network_service.create_sample_network("ieee14")
        logger.info("Sample network (IEEE 14 bus) created successfully")
    except Exception as e:
        logger.warning(f"Failed to create sample network: {e}")

    yield

    # シャットダウン時のクリーンアップ
    logger.info("Shutting down PowSyBl Advanced Analysis Engine...")


# FastAPIアプリケーション
app = FastAPI(
    title="PowSyBl Advanced Analysis Engine",
    description="変電所デジタルツイン向け高度電力系統分析エンジン",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ヘルスチェック・ネットワーク管理エンドポイント
# ============================================================================

@app.get("/")
async def root():
    """ルートエンドポイント - ヘルスチェック"""
    return {
        "service": "PowSyBl Advanced Analysis Engine",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }


@app.get("/networks")
async def list_networks():
    """ネットワークリストを取得"""
    return {
        "networks": list(network_service.networks.keys())
    }


@app.get("/networks/{network_id}/info")
async def get_network_info(network_id: str):
    """ネットワーク情報を取得"""
    try:
        info = network_service.get_network_info(network_id)
        return info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/networks/create-sample/{network_id}")
async def create_sample_network(network_id: str = "sample"):
    """サンプルネットワークを作成"""
    try:
        network_service.create_sample_network(network_id)
        return {
            "status": "created",
            "network_id": network_id,
            "message": "Sample network created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 潮流計算エンドポイント
# ============================================================================

@app.post("/api/v1/loadflow", response_model=LoadFlowResult)
async def run_loadflow(request: LoadFlowRequest):
    """
    潮流計算を実行
    AC Load Flow または DC Load Flow
    """
    try:
        result = loadflow_service.run_loadflow(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Load flow calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# セキュリティ分析エンドポイント
# ============================================================================

@app.post("/api/v1/security", response_model=SecurityAnalysisResult)
async def run_security_analysis(request: SecurityAnalysisRequest):
    """
    セキュリティ分析を実行
    N-1/N-K コンティンジェンシー分析
    """
    try:
        result = security_service.run_security_analysis(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Security analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/security/{network_id}/n1-contingencies")
async def generate_n1_contingencies(network_id: str):
    """
    N-1コンティンジェンシーを自動生成
    全ての送電線・変圧器に対する単一故障シナリオ
    """
    try:
        contingencies = security_service.generate_n1_contingencies(network_id)
        return {
            "network_id": network_id,
            "count": len(contingencies),
            "contingencies": [c.dict() for c in contingencies]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 感度分析エンドポイント
# ============================================================================

@app.post("/api/v1/sensitivity", response_model=SensitivityAnalysisResult)
async def run_sensitivity_analysis(request: SensitivityAnalysisRequest):
    """
    感度分析を実行
    PTDF, PSDF, DCDF 等の感度係数を計算
    """
    try:
        result = sensitivity_service.run_sensitivity_analysis(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sensitivity analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sensitivity/{network_id}/generate-ptdf")
async def generate_ptdf_factors(
    network_id: str,
    monitored_branches: list[str],
    injection_points: list[str]
):
    """
    PTDF用の感度係数を自動生成
    """
    try:
        factors = sensitivity_service.generate_ptdf_factors(
            network_id,
            monitored_branches,
            injection_points
        )
        return {
            "network_id": network_id,
            "count": len(factors),
            "factors": [f.dict() for f in factors]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 統合分析エンドポイント
# ============================================================================

@app.post("/api/v1/comprehensive-analysis/{network_id}")
async def run_comprehensive_analysis(network_id: str):
    """
    包括的分析を実行
    潮流計算 → セキュリティ分析 → 感度分析を順次実行
    """
    try:
        results = {}

        # 1. 潮流計算
        lf_request = LoadFlowRequest(network_id=network_id)
        results['loadflow'] = loadflow_service.run_loadflow(lf_request)

        # 2. N-1セキュリティ分析
        contingencies = security_service.generate_n1_contingencies(network_id)
        sec_request = SecurityAnalysisRequest(
            network_id=network_id,
            contingencies=contingencies[:10]  # 最初の10個のみ（デモ用）
        )
        results['security'] = security_service.run_security_analysis(sec_request)

        return {
            "network_id": network_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": results
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comprehensive analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
