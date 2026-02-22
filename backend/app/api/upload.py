"""
파일 업로드 API
"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import logging

from app.config import settings
from app.models.session import FileUploadResponse
from app.database.memory_store import memory_store
from app.services.kpi_pipeline import KPIPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/files", response_model=FileUploadResponse)
async def upload_files(
    hira_file: UploadFile = File(..., description="HIRA 파일 (Excel)"),
    smc_file: UploadFile = File(..., description="SMC 파일 (Excel)"),
    hospital: str = Form(..., description="병원명 (대전 or 유성)")
):
    """
    HIRA/SMC 파일 업로드 및 KPI 계산

    - **hira_file**: 심평원 DRG 기준 파일
    - **smc_file**: 선메디컬센터 내부 실적 파일
    - **hospital**: 병원명 ("대전" 또는 "유성")
    """
    logger.info(f"파일 업로드 시작: {hospital}")

    # 세션 생성
    session_id = memory_store.create_session(hospital)

    try:
        # 업로드 디렉토리 생성
        upload_dir = settings.UPLOAD_DIR / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        hira_path = upload_dir / "hira.xlsx"
        smc_path = upload_dir / "smc.xlsx"

        with open(hira_path, "wb") as buffer:
            shutil.copyfileobj(hira_file.file, buffer)

        with open(smc_path, "wb") as buffer:
            shutil.copyfileobj(smc_file.file, buffer)

        logger.info(f"파일 저장 완료: {upload_dir}")

        # KPI 파이프라인 실행
        logger.info("KPI 파이프라인 실행")
        pipeline = KPIPipeline()
        result = pipeline.run_pipeline(
            str(hira_path),
            str(smc_path),
            hospital
        )

        # 결과 저장
        memory_store.save_kpi_data(
            session_id=session_id,
            hospital=hospital,
            period='off_season',
            summary_kpi=result['summary_kpi'],
            disease_kpis_off_season=result['disease_kpis_off_season'],
            disease_kpis_normal=result['disease_kpis_normal'],
            doctor_kpis_off_season=result['doctor_kpis_off_season'],
            doctor_kpis_normal=result['doctor_kpis_normal'],
            department_kpis_off_season=result['department_kpis_off_season'],
            department_kpis_normal=result['department_kpis_normal'],
            insights_off_season=result['insights_off_season'],
            insights_normal=result['insights_normal']
        )

        # 세션 상태 업데이트
        memory_store.update_session_status(
            session_id,
            "completed",
            metadata=result['metadata']
        )

        logger.info(f"KPI 계산 완료: {session_id}")

        return FileUploadResponse(
            session_id=session_id,
            status="completed",
            message="파일 업로드 및 KPI 계산 완료",
            metadata=result['metadata']
        )

    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}", exc_info=True)

        # 세션 상태 업데이트
        memory_store.update_session_status(
            session_id,
            "failed",
            metadata={'error': str(e)}
        )

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session_id}")
async def get_upload_status(session_id: str):
    """
    업로드 세션 상태 조회
    """
    session = memory_store.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    return {
        "session_id": session.session_id,
        "hospital": session.hospital,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "metadata": session.metadata
    }
