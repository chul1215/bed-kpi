"""
KPI 산출 엔진

핵심 KPI 계산 로직을 구현합니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from typing import Dict, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


class KPICalculator:
    """KPI 산출 클래스"""

    @staticmethod
    def calculate_disease_kpi(
        disease_row: pd.Series,
        target_los: float
    ) -> Dict[str, float]:
        """
        질환별 KPI 계산

        Args:
            disease_row: 질환 집계 행 (patient_count, total_bed_days, current_los 포함)
            target_los: HIRA 목표 LOS

        Returns:
            KPI 딕셔너리
        """
        patient_count = disease_row['patient_count']
        total_bed_days = disease_row['total_bed_days']
        current_los = disease_row['current_los']

        # 최소 환자수 기준 확인
        if patient_count < settings.MIN_PATIENT_COUNT:
            return {
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': target_los,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        # LOS 갭 계산 (양방향 유지)
        los_gap = target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': target_los,
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    @staticmethod
    def calculate_doctor_kpi(
        doctor_row: pd.Series,
        disease_target_los_map: Dict[str, float],
        doctor_disease_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        의료진별 KPI 계산 (가중 평균 목표 LOS)

        Args:
            doctor_row: 의료진 집계 행
            disease_target_los_map: 질환별 목표 LOS 매핑 {'질환명': target_los}
            doctor_disease_df: 의료진-질환 집계 데이터

        Returns:
            KPI 딕셔너리
        """
        doctor_name = doctor_row['doctor']
        patient_count = doctor_row['patient_count']
        total_bed_days = doctor_row['total_bed_days']
        current_los = doctor_row['current_los']

        # 최소 환자수 기준 확인
        if patient_count < settings.MIN_PATIENT_COUNT:
            return {
                'doctor': doctor_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        # 의료진의 질환별 데이터 추출
        doctor_diseases = doctor_disease_df[
            doctor_disease_df['doctor'] == doctor_name
        ].copy()

        if doctor_diseases.empty:
            return {
                'doctor': doctor_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_disease_data'
            }

        # 가중 평균 목표 LOS 계산
        # target_los = Σ(질환_목표_LOS × 질환_환자수_비중)
        weighted_target_los = 0
        total_matched = 0

        for _, disease_row in doctor_diseases.iterrows():
            diagnosis = disease_row['diagnosis']
            disease_patient_count = disease_row['patient_count']

            if diagnosis in disease_target_los_map:
                disease_target = disease_target_los_map[diagnosis]
                patient_weight = disease_patient_count / patient_count
                weighted_target_los += disease_target * patient_weight
                total_matched += disease_patient_count

        # 매칭되지 않은 질환이 있으면 가중치 조정
        if total_matched < patient_count:
            # 매칭율이 낮으면 경고
            match_rate = (total_matched / patient_count) * 100
            logger.warning(
                f"의료진 {doctor_name} DRG 매칭율 낮음: {match_rate:.1f}% "
                f"({total_matched}/{patient_count})"
            )

        # LOS 갭 계산
        los_gap = weighted_target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'doctor': doctor_name,
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': round(weighted_target_los, 2),
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    @staticmethod
    def calculate_department_kpi(
        department_row: pd.Series,
        disease_target_los_map: Dict[str, float],
        department_disease_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        진료과별 KPI 계산 (질환별 가중 평균)

        Args:
            department_row: 진료과 집계 행
            disease_target_los_map: 질환별 목표 LOS 매핑
            department_disease_df: 진료과-질환 집계 데이터

        Returns:
            KPI 딕셔너리
        """
        department_name = department_row['department']
        patient_count = department_row['patient_count']
        total_bed_days = department_row['total_bed_days']
        current_los = department_row['current_los']

        # 최소 환자수 기준 확인
        if patient_count < settings.MIN_PATIENT_COUNT:
            return {
                'department': department_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        # 진료과의 질환별 데이터 추출
        dept_diseases = department_disease_df[
            department_disease_df['department'] == department_name
        ].copy()

        if dept_diseases.empty:
            return {
                'department': department_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_disease_data'
            }

        # 가중 평균 목표 LOS 계산
        weighted_target_los = 0
        total_matched = 0

        for _, disease_row in dept_diseases.iterrows():
            diagnosis = disease_row['diagnosis']
            disease_patient_count = disease_row['patient_count']

            if diagnosis in disease_target_los_map:
                disease_target = disease_target_los_map[diagnosis]
                patient_weight = disease_patient_count / patient_count
                weighted_target_los += disease_target * patient_weight
                total_matched += disease_patient_count

        if total_matched < patient_count:
            match_rate = (total_matched / patient_count) * 100
            logger.warning(
                f"진료과 {department_name} DRG 매칭율 낮음: {match_rate:.1f}%"
            )

        # LOS 갭 계산
        los_gap = weighted_target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'department': department_name,
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': round(weighted_target_los, 2),
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    @staticmethod
    def calculate_summary_kpi(
        disease_kpis: pd.DataFrame,
        bed_count: int = 300,
        period_days: int = 122
    ) -> Dict[str, float]:
        """
        요약 KPI 계산 (전체 평균)

        Args:
            disease_kpis: 질환별 KPI 데이터프레임
            bed_count: 병상 수 (기본값: 300)
            period_days: 기간 일수 (기본값: 122일 = 비수기)

        Returns:
            요약 KPI 딕셔너리
        """
        # 계산된 항목만 필터링
        valid_kpis = disease_kpis[disease_kpis['status'] == 'calculated'].copy()

        if valid_kpis.empty:
            return {
                'average_los_gap': 0,
                'total_additional_bed_days': 0,
                'current_utilization_rate': 0,
                'target_utilization_rate': 0,
                'patient_count': 0
            }

        # 평균 LOS 갭
        average_los_gap = valid_kpis['los_gap'].mean()

        # 추가 병상일수 합계
        total_additional_bed_days = valid_kpis['additional_bed_days'].sum()

        # 현재 가동률
        total_current_bed_days = valid_kpis['total_bed_days'].sum()
        available_bed_days = bed_count * period_days
        current_utilization_rate = (total_current_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0

        # 목표 가동률
        total_target_bed_days = total_current_bed_days + total_additional_bed_days
        target_utilization_rate = (total_target_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0

        # 총 환자수
        total_patient_count = valid_kpis['patient_count'].sum()

        return {
            'average_los_gap': round(average_los_gap, 2),
            'total_additional_bed_days': round(total_additional_bed_days, 0),
            'current_utilization_rate': round(current_utilization_rate, 1),
            'target_utilization_rate': round(target_utilization_rate, 1),
            'patient_count': int(total_patient_count)
        }
