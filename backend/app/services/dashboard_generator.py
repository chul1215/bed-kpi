"""
대시보드 HTML 생성 서비스

Jinja2 템플릿을 사용하여 동적 HTML 대시보드를 생성합니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """대시보드 HTML 생성 클래스"""

    TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

    def __init__(self):
        """Jinja2 환경 초기화"""
        self.env = Environment(
            loader=FileSystemLoader(self.TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render_home(\
        self,
        summary_kpi: Dict[str, float],
        doctor_kpis: pd.DataFrame,
        disease_kpis: pd.DataFrame,
        insights: List[str],
        hospital: str = '대전',
        period: str = 'off_season',
        doctor_disease_data: Dict[str, List[Dict]] = None
    ) -> str:
        """
        홈 화면 렌더링

        Args:
            summary_kpi: 요약 KPI 딕셔너리
            doctor_kpis: 의료진별 KPI 데이터프레임
            disease_kpis: 질환별 KPI 데이터프레임
            insights: 인사이트 리스트
            hospital: 병원명
            period: 기간
            doctor_disease_data: 의료진별 질환 데이터 (토글용)

        Returns:
            렌더링된 HTML 문자열
        """
        # 의료진별 TOP 6 추출 (환자수 기준 정렬)
        doctor_disease_top6 = []
        doctor_all_data = []
        department_list = []

        if len(doctor_kpis) > 0:
            # NaN을 None으로 변환
            doctor_kpis_clean = doctor_kpis.copy()
            doctor_kpis_clean['los_gap'] = doctor_kpis_clean['los_gap'].where(pd.notna(doctor_kpis_clean['los_gap']), None)
            doctor_kpis_clean['additional_bed_days'] = doctor_kpis_clean['additional_bed_days'].where(pd.notna(doctor_kpis_clean['additional_bed_days']), None)

            # 환자수 기준 TOP 6
            doctor_with_data = doctor_kpis_clean[doctor_kpis_clean['patient_count'] > 0]
            if len(doctor_with_data) > 0:
                doctor_disease_top6 = doctor_with_data.nlargest(6, 'patient_count').to_dict('records')

            # 전체 의료진 데이터 (검색용)
            doctor_all_data = doctor_kpis_clean.to_dict('records')

            # 진료과 목록
            department_list = sorted(doctor_kpis['department'].unique().tolist())

        # 진단별 TOP 6 추출 (추가 재원일수 기준 정렬)
        disease_top6 = []
        if len(disease_kpis) > 0:
            # NaN을 None으로 변환
            disease_kpis_clean = disease_kpis.copy()
            disease_kpis_clean['los_gap'] = disease_kpis_clean['los_gap'].where(pd.notna(disease_kpis_clean['los_gap']), None)
            disease_kpis_clean['additional_bed_days'] = disease_kpis_clean['additional_bed_days'].where(pd.notna(disease_kpis_clean['additional_bed_days']), None)

            # 추가 재원일수 기준 TOP 6 (절댓값 기준, 임팩트 큰 순서)
            disease_with_data = disease_kpis_clean[disease_kpis_clean['additional_bed_days'].notna()]
            if len(disease_with_data) > 0:
                disease_with_data['abs_additional_bed_days'] = disease_with_data['additional_bed_days'].abs()
                disease_top6 = disease_with_data.nlargest(6, 'abs_additional_bed_days').to_dict('records')

        # 진료과별 요약 (샘플)
        department_summary = []

        # Summary 키 매핑
        summary = {
            'avg_los_gap': summary_kpi.get('average_los_gap', 0),
            'total_additional_bed_days': summary_kpi.get('total_additional_bed_days', 0),
            'patient_count': summary_kpi.get('patient_count', 0),
            'occupancy_improvement': summary_kpi.get('target_utilization_rate', 0) - summary_kpi.get('current_utilization_rate', 0)
        }

        template = self.env.get_template('index.html')
        html = template.render(
            title='선메디컬센터 병상가동 KPI 산출',
            hospital=hospital,
            period=period,
            period_name=self._get_period_label(period),
            summary=summary,
            doctor_disease_top6=doctor_disease_top6,
            disease_top6=disease_top6,
            doctor_all_data=doctor_all_data,
            department_list=department_list,
            department_summary=department_summary,
            insights=insights,
            doctor_disease_data=doctor_disease_data or {}
        )

        return html

    def render_department(\
        self,
        department_kpis: pd.DataFrame,
        doctor_kpis_by_dept: Dict[str, pd.DataFrame],
        hospital: str = '대전',
        period: str = 'off_season'
    ) -> str:
        """
        진료과 뷰 렌더링

        Args:
            department_kpis: 진료과별 KPI 데이터프레임
            doctor_kpis_by_dept: 진료과별 의료진 KPI 딕셔너리
            hospital: 병원명
            period: 기간

        Returns:
            렌더링된 HTML 문자열
        """
        # DataFrame을 리스트로 변환
        doctor_kpis_by_dept_list = {}
        for dept, df in doctor_kpis_by_dept.items():
            doctor_kpis_by_dept_list[dept] = self._format_dataframe(df)

        template = self.env.get_template('department.html')
        html = template.render(
            title='선메디컬센터 병상가동 KPI 산출',
            hospital=hospital,
            period=period,
            period_label=self._get_period_label(period),
            department_kpis=self._format_dataframe(department_kpis),
            doctor_kpis_by_dept=doctor_kpis_by_dept_list
        )

        return html

    def render_doctor(\
        self,
        doctor_name: str,
        doctor_kpi: Dict[str, float],
        disease_kpis: pd.DataFrame,
        hospital: str = '대전',
        period: str = 'off_season'
    ) -> str:
        """
        의료진 상세 뷰 렌더링

        Args:
            doctor_name: 의료진명
            doctor_kpi: 의료진 KPI 딕셔너리
            disease_kpis: 의료진의 질환별 KPI 데이터프레임
            hospital: 병원명
            period: 기간

        Returns:
            렌더링된 HTML 문자열
        """
        # 병상 수 및 기간 일수 (설정에서 가져와야 함)
        bed_count = 300
        period_days = 122 if period == 'off_season' else 243

        template = self.env.get_template('doctor.html')
        html = template.render(
            title='선메디컬센터 병상가동 KPI 산출',
            hospital=hospital,
            period=period,
            period_label=self._get_period_label(period),
            doctor_name=doctor_name,
            doctor_kpi=doctor_kpi,
            disease_kpis=self._format_dataframe(disease_kpis),
            bed_count=bed_count,
            period_days=period_days
        )

        return html

    def render_disease(\
        self,
        disease_name: str,
        disease_info: Dict[str, float],
        doctor_distribution: pd.DataFrame,
        hospital: str = '대전',
        period: str = 'off_season'
    ) -> str:
        """
        질환 뷰 렌더링

        Args:
            disease_name: 질환명
            disease_info: 질환 정보 딕셔너리 (target_los, current_los, los_gap 등)
            doctor_distribution: 질환별 의료진 분포
            hospital: 병원명
            period: 기간

        Returns:
            렌더링된 HTML 문자열
        """
        template = self.env.get_template('disease.html')
        html = template.render(
            title='선메디컬센터 병상가동 KPI 산출',
            hospital=hospital,
            period=period,
            period_label=self._get_period_label(period),
            disease_name=disease_name,
            disease_info=disease_info,
            doctor_distribution=self._format_dataframe(doctor_distribution)
        )

        return html

    @staticmethod
    def _get_period_label(period: str) -> str:
        """기간 라벨 반환"""
        if period == 'off_season':
            return '비수기 (3-4월, 11-12월)'
        elif period == 'normal':
            return '통상기간 (1-2월, 5-10월)'
        else:
            return period

    @staticmethod
    def _format_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """DataFrame을 리스트로 변환"""
        return df.to_dict('records')

    @staticmethod
    def _prepare_doctor_disease_data(\
        doctor_kpis: pd.DataFrame,
        top_n: int = 6
    ) -> List[Dict[str, Any]]:
        """
        의료진별 질환 TOP N 데이터 준비

        Args:
            doctor_kpis: 의료진별 KPI 데이터프레임
            top_n: 상위 개수

        Returns:
            의료진별 질환 데이터 리스트
        """
        # 이 메서드는 실제로는 disease_kpis와 doctor_disease_df가 필요합니다.
        # 현재는 의료진 정보만 반환
        result = []

        for _, row in doctor_kpis.head(10).iterrows():
            # NaN 값 처리
            patient_count = row.get('patient_count', 0)
            los_gap = row.get('los_gap', 0)
            additional_bed_days = row.get('additional_bed_days', 0)

            # NaN을 0으로 변환
            import pandas as pd
            if pd.isna(patient_count):
                patient_count = 0
            if pd.isna(los_gap):
                los_gap = 0
            if pd.isna(additional_bed_days):
                additional_bed_days = 0

            result.append({
                'doctor': row.get('doctor', ''),
                'department': row.get('department', ''),
                'patient_count': int(patient_count),
                'los_gap': float(los_gap),
                'additional_bed_days': int(additional_bed_days),
                'expanded': False,
                'diseases': []  # 실제로는 disease_kpis에서 추출
            })

        return result

    def render_upload(self) -> str:
        """업로드 페이지 렌더링"""
        template = self.env.get_template('upload.html')
        html = template.render(
            title='데이터 업로드',
            hospital='대전',
            period='off_season'
        )
        return html
