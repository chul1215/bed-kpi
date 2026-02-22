"""
세션 및 KPI 데이터 모델
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import pandas as pd


class UploadSession(BaseModel):
    """업로드 세션"""
    session_id: str
    hospital: str  # "대전" or "유성"
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "processing"  # "processing", "completed", "failed"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class KPIData(BaseModel):
    """KPI 데이터 저장 모델"""
    session_id: str
    hospital: str
    period: str  # "off_season" or "normal"

    # 요약 KPI
    summary_kpi: Dict[str, float] = Field(default_factory=dict)

    # 질환별 KPI (DataFrame을 dict로 변환하여 저장)
    disease_kpis_off_season: Dict[str, Any] = Field(default_factory=dict)
    disease_kpis_normal: Dict[str, Any] = Field(default_factory=dict)

    # 의료진별 KPI
    doctor_kpis_off_season: Dict[str, Any] = Field(default_factory=dict)
    doctor_kpis_normal: Dict[str, Any] = Field(default_factory=dict)

    # 진료과별 KPI
    department_kpis_off_season: Dict[str, Any] = Field(default_factory=dict)
    department_kpis_normal: Dict[str, Any] = Field(default_factory=dict)

    # 인사이트
    insights_off_season: List[str] = Field(default_factory=list)
    insights_normal: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class FileUploadRequest(BaseModel):
    """파일 업로드 요청"""
    hospital: str


class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    session_id: str
    status: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
