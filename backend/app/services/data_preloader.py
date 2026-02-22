"""
사전 식립 데이터 로더
애플리케이션 시작 시 자동으로 HIRA/SMC 데이터를 로드하여 세션을 생성
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.kpi_pipeline import KPIPipeline
from app.database.memory_store import memory_store

logger = logging.getLogger(__name__)


class DataPreloader:
    """사전 식립 데이터 로더"""

    def __init__(self):
        # KDRG 파일 경로 전달
        kdrg_file = settings.PRELOADED_KDRG_FILE if hasattr(settings, 'PRELOADED_KDRG_FILE') else None
        self.pipeline = KPIPipeline(kdrg_file_path=str(kdrg_file) if kdrg_file else None)
        self.preloaded_sessions = {}  # {hospital: session_id}

    def load_preloaded_data(self) -> dict:
        """
        사전 식립 데이터 로드

        Returns:
            {
                'success': bool,
                'sessions': {'대전': session_id, '유성': session_id},
                'message': str
            }
        """
        if not settings.ENABLE_PRELOADED_DATA:
            logger.info("사전 식립 데이터 비활성화됨")
            return {
                'success': False,
                'sessions': {},
                'message': '사전 식립 데이터가 비활성화되어 있습니다'
            }

        # 파일 존재 확인
        hira_file = settings.PRELOADED_HIRA_FILE
        smc_file = settings.PRELOADED_SMC_FILE

        if not hira_file.exists():
            logger.warning(f"HIRA 파일 없음: {hira_file}")
            return {
                'success': False,
                'sessions': {},
                'message': f'HIRA 파일을 찾을 수 없습니다: {hira_file}'
            }

        if not smc_file.exists():
            logger.warning(f"SMC 파일 없음: {smc_file}")
            return {
                'success': False,
                'sessions': {},
                'message': f'SMC 파일을 찾을 수 없습니다: {smc_file}'
            }

        logger.info("=" * 80)
        logger.info("사전 식립 데이터 로딩 시작")
        logger.info("=" * 80)

        sessions = {}

        # 대전/유성 병원별로 세션 생성
        for hospital in ["대전", "유성"]:
            try:
                logger.info(f"\n{hospital}선병원 데이터 로딩 시작...")

                # 세션 생성
                session_id = memory_store.create_session(hospital)
                logger.info(f"세션 ID: {session_id}")

                # KPI 파이프라인 실행 (4분기 필터링)
                result = self.pipeline.run_pipeline(
                    str(hira_file),
                    str(smc_file),
                    hospital,
                    filter_quarter=4  # HIRA 4분기 데이터와 일치
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

                sessions[hospital] = session_id

                logger.info(f"✅ {hospital}선병원 데이터 로딩 완료")
                logger.info(f"   - HIRA: {result['metadata']['hira_count']}건")
                logger.info(f"   - SMC: {result['metadata']['smc_count']}건")
                logger.info(f"   - 비수기: {result['metadata']['off_season_count']}건")
                logger.info(f"   - 통상기간: {result['metadata']['normal_count']}건")
                logger.info(f"   - 매칭률: {result['metadata']['match_rate']:.1f}%")

            except Exception as e:
                logger.error(f"❌ {hospital}선병원 데이터 로딩 실패: {str(e)}", exc_info=True)
                continue

        self.preloaded_sessions = sessions

        logger.info("\n" + "=" * 80)
        logger.info(f"사전 식립 데이터 로딩 완료: {len(sessions)}개 병원")
        logger.info("=" * 80)

        return {
            'success': len(sessions) > 0,
            'sessions': sessions,
            'message': f'{len(sessions)}개 병원 데이터 로딩 완료'
        }

    def get_default_session(self, hospital: str = "대전") -> Optional[str]:
        """
        기본 세션 ID 조회

        Args:
            hospital: 병원명 ("대전" or "유성")

        Returns:
            session_id 또는 None
        """
        return self.preloaded_sessions.get(hospital)


# 싱글톤 인스턴스
data_preloader = DataPreloader()
