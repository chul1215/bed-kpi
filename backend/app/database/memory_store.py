"""
In-memory 데이터 저장소
간단한 세션 관리 및 KPI 데이터 저장
"""
from __future__ import annotations

from typing import Dict, Optional
import uuid
from datetime import datetime
import pandas as pd

from app.models.session import UploadSession, KPIData


class MemoryStore:
    """메모리 기반 데이터 저장소"""

    def __init__(self):
        self.sessions: Dict[str, UploadSession] = {}
        self.kpi_data: Dict[str, KPIData] = {}

    def create_session(self, hospital: str) -> str:
        """새로운 세션 생성"""
        session_id = str(uuid.uuid4())
        session = UploadSession(
            session_id=session_id,
            hospital=hospital,
            created_at=datetime.now(),
            status="processing"
        )
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """세션 조회"""
        return self.sessions.get(session_id)

    def update_session_status(self, session_id: str, status: str, metadata: Dict = None):
        """세션 상태 업데이트"""
        if session_id in self.sessions:
            self.sessions[session_id].status = status
            if metadata:
                self.sessions[session_id].metadata.update(metadata)

    def save_kpi_data(self, session_id: str, hospital: str, period: str, **kwargs):
        """KPI 데이터 저장"""
        if session_id not in self.kpi_data:
            self.kpi_data[session_id] = KPIData(
                session_id=session_id,
                hospital=hospital,
                period=period
            )

        kpi = self.kpi_data[session_id]

        # 요약 KPI 저장
        if 'summary_kpi' in kwargs:
            kpi.summary_kpi = kwargs['summary_kpi']

        # 질환별 KPI 저장 (DataFrame → dict)
        if 'disease_kpis_off_season' in kwargs:
            df = kwargs['disease_kpis_off_season']
            if isinstance(df, pd.DataFrame):
                kpi.disease_kpis_off_season = df.to_dict('records')

        if 'disease_kpis_normal' in kwargs:
            df = kwargs['disease_kpis_normal']
            if isinstance(df, pd.DataFrame):
                kpi.disease_kpis_normal = df.to_dict('records')

        # 의료진별 KPI 저장
        if 'doctor_kpis_off_season' in kwargs:
            df = kwargs['doctor_kpis_off_season']
            if isinstance(df, pd.DataFrame):
                kpi.doctor_kpis_off_season = df.to_dict('records')

        if 'doctor_kpis_normal' in kwargs:
            df = kwargs['doctor_kpis_normal']
            if isinstance(df, pd.DataFrame):
                kpi.doctor_kpis_normal = df.to_dict('records')

        # 진료과별 KPI 저장
        if 'department_kpis_off_season' in kwargs:
            df = kwargs['department_kpis_off_season']
            if isinstance(df, pd.DataFrame):
                kpi.department_kpis_off_season = df.to_dict('records')

        if 'department_kpis_normal' in kwargs:
            df = kwargs['department_kpis_normal']
            if isinstance(df, pd.DataFrame):
                kpi.department_kpis_normal = df.to_dict('records')

        # 인사이트 저장
        if 'insights_off_season' in kwargs:
            kpi.insights_off_season = kwargs['insights_off_season']

        if 'insights_normal' in kwargs:
            kpi.insights_normal = kwargs['insights_normal']

    def get_kpi_data(self, session_id: str) -> Optional[KPIData]:
        """KPI 데이터 조회"""
        return self.kpi_data.get(session_id)

    def get_summary_kpi(self, session_id: str, hospital: str, period: str) -> Dict:
        """요약 KPI 조회"""
        kpi = self.get_kpi_data(session_id)
        if kpi:
            return kpi.summary_kpi
        return {}

    def get_doctor_kpis(self, session_id: str, hospital: str, period: str) -> pd.DataFrame:
        """의료진 KPI 조회"""
        kpi = self.get_kpi_data(session_id)
        if not kpi:
            return pd.DataFrame()

        if period == "off_season":
            data = kpi.doctor_kpis_off_season
        else:
            data = kpi.doctor_kpis_normal

        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()

    def get_disease_kpis(self, session_id: str, hospital: str, period: str) -> pd.DataFrame:
        """질환 KPI 조회"""
        kpi = self.get_kpi_data(session_id)
        if not kpi:
            return pd.DataFrame()

        if period == "off_season":
            data = kpi.disease_kpis_off_season
        else:
            data = kpi.disease_kpis_normal

        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()

    def get_department_kpis(self, session_id: str, hospital: str, period: str) -> pd.DataFrame:
        """진료과 KPI 조회"""
        kpi = self.get_kpi_data(session_id)
        if not kpi:
            return pd.DataFrame()

        if period == "off_season":
            data = kpi.department_kpis_off_season
        else:
            data = kpi.department_kpis_normal

        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()

    def get_insights(self, session_id: str, hospital: str, period: str) -> list:
        """인사이트 조회"""
        kpi = self.get_kpi_data(session_id)
        if not kpi:
            return []

        if period == "off_season":
            return kpi.insights_off_season
        else:
            return kpi.insights_normal


# 싱글톤 인스턴스
memory_store = MemoryStore()
