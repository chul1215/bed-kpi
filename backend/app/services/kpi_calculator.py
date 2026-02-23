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
    def calculate_adrg_kpi(
        adrg_row: pd.Series
    ) -> Dict[str, float]:
        """
        ADRG별 KPI 계산

        Args:
            adrg_row: ADRG 집계 행 (adrg_code, adrg_name, patient_count, total_bed_days, current_los, target_los 포함)

        Returns:
            KPI 딕셔너리
        """
        adrg_code = adrg_row['adrg_code']
        adrg_name = adrg_row.get('adrg_name', adrg_code)
        patient_count = adrg_row['patient_count']
        total_bed_days = adrg_row['total_bed_days']
        current_los = adrg_row['current_los']
        target_los = adrg_row['target_los']

        # 최소 환자수 기준 확인
        if patient_count < settings.MIN_PATIENT_COUNT:
            return {
                'adrg_code': adrg_code,
                'adrg_name': adrg_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': target_los,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        if pd.isna(target_los):
            return {
                'adrg_code': adrg_code,
                'adrg_name': adrg_name,
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_target_los'
            }

        # LOS 갭 계산 (양방향 유지)
        los_gap = target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'adrg_code': adrg_code,
            'adrg_name': adrg_name,
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': target_los,
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    @staticmethod
    def calculate_diagnosis_kpi(
        diagnosis_row: pd.Series
    ) -> Dict[str, float]:
        """
        진단명별 KPI 계산 (하위 호환성 유지)

        NOTE: calculate_adrg_kpi 사용 권장. 이 함수는 레거시 지원용입니다.

        Args:
            diagnosis_row: 진단명 집계 행 (patient_count, total_bed_days, current_los, target_los 포함)

        Returns:
            KPI 딕셔너리
        """
        patient_count = diagnosis_row['patient_count']
        total_bed_days = diagnosis_row['total_bed_days']
        current_los = diagnosis_row['current_los']
        target_los = diagnosis_row['target_los']

        # 최소 환자수 기준 확인
        if patient_count < settings.MIN_PATIENT_COUNT:
            return {
                'diagnosis': diagnosis_row['diagnosis'],
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': target_los,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        if pd.isna(target_los):
            return {
                'diagnosis': diagnosis_row['diagnosis'],
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_target_los'
            }

        # LOS 갭 계산 (양방향 유지)
        los_gap = target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'diagnosis': diagnosis_row['diagnosis'],
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': target_los,
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    # 하위 호환성 별칭
    calculate_disease_kpi = calculate_diagnosis_kpi

    @staticmethod
    def calculate_doctor_kpi_by_adrg(
        doctor_row: pd.Series,
        adrg_target_los_map: Dict[str, float],
        doctor_adrg_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        의료진별 KPI 계산 (ADRG 기반 가중 평균 목표 LOS)

        Args:
            doctor_row: 의료진 집계 행
            adrg_target_los_map: ADRG별 목표 LOS 매핑 {'adrg_code': target_los}
            doctor_adrg_df: 의료진-ADRG 집계 데이터

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
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        # 의료진의 ADRG별 데이터 추출
        doctor_adrgs = doctor_adrg_df[
            doctor_adrg_df['doctor'] == doctor_name
        ].copy()

        if doctor_adrgs.empty:
            return {
                'doctor': doctor_name,
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_adrg_data'
            }

        # 가중 평균 목표 LOS 계산
        # target_los = Σ(ADRG_목표_LOS × ADRG_환자수_비중)
        weighted_target_los = 0
        total_matched = 0

        for _, adrg_row in doctor_adrgs.iterrows():
            adrg_code = adrg_row['adrg_code']
            adrg_patient_count = adrg_row['patient_count']

            if adrg_code in adrg_target_los_map:
                adrg_target = adrg_target_los_map[adrg_code]
                patient_weight = adrg_patient_count / patient_count
                weighted_target_los += adrg_target * patient_weight
                total_matched += adrg_patient_count

        # 매칭되지 않은 ADRG가 있으면 가중치 조정
        if total_matched < patient_count:
            # 매칭율이 낮으면 경고
            match_rate = (total_matched / patient_count) * 100
            logger.warning(
                f"의료진 {doctor_name} ADRG 매칭율: {match_rate:.1f}% "
                f"({total_matched}/{patient_count})"
            )

        # 매칭된 환자가 없으면 None 반환
        if total_matched == 0 or weighted_target_los == 0:
            return {
                'doctor': doctor_name,
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': round(current_los, 2),
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_target_los'
            }

        # LOS 갭 계산
        los_gap = weighted_target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'doctor': doctor_name,
            'department': doctor_row.get('department', ''),
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': round(weighted_target_los, 2),
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'match_rate': round((total_matched / patient_count) * 100, 1),
            'status': 'calculated'
        }

    @staticmethod
    def calculate_doctor_kpi_by_diagnosis(
        doctor_row: pd.Series,
        diagnosis_target_los_map: Dict[str, float],
        doctor_diagnosis_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        의료진별 KPI 계산 (진단명 기반 가중 평균 목표 LOS - 하위 호환성)

        NOTE: calculate_doctor_kpi_by_adrg 사용 권장. 이 함수는 레거시 지원용입니다.

        Args:
            doctor_row: 의료진 집계 행
            diagnosis_target_los_map: 진단명별 목표 LOS 매핑 {'진단명': target_los}
            doctor_diagnosis_df: 의료진-진단명 집계 데이터

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
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'below_minimum'
            }

        # 의료진의 진단명별 데이터 추출
        doctor_diagnoses = doctor_diagnosis_df[
            doctor_diagnosis_df['doctor'] == doctor_name
        ].copy()

        if doctor_diagnoses.empty:
            return {
                'doctor': doctor_name,
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': current_los,
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_diagnosis_data'
            }

        # 가중 평균 목표 LOS 계산
        # target_los = Σ(진단명_목표_LOS × 진단명_환자수_비중)
        weighted_target_los = 0
        total_matched = 0

        for _, diagnosis_row in doctor_diagnoses.iterrows():
            diagnosis = diagnosis_row['diagnosis']
            diagnosis_patient_count = diagnosis_row['patient_count']

            if diagnosis in diagnosis_target_los_map:
                diagnosis_target = diagnosis_target_los_map[diagnosis]
                patient_weight = diagnosis_patient_count / patient_count
                weighted_target_los += diagnosis_target * patient_weight
                total_matched += diagnosis_patient_count

        # 매칭되지 않은 진단명이 있으면 가중치 조정
        if total_matched < patient_count:
            # 매칭율이 낮으면 경고
            match_rate = (total_matched / patient_count) * 100
            logger.warning(
                f"의료진 {doctor_name} 진단명 매칭율 낮음: {match_rate:.1f}% "
                f"({total_matched}/{patient_count})"
            )

        # 매칭된 환자가 없으면 None 반환
        if total_matched == 0 or weighted_target_los == 0:
            return {
                'doctor': doctor_name,
                'department': doctor_row.get('department', ''),
                'patient_count': patient_count,
                'total_bed_days': total_bed_days,
                'current_los': round(current_los, 2),
                'target_los': None,
                'los_gap': None,
                'additional_bed_days': None,
                'status': 'no_target_los'
            }

        # LOS 갭 계산
        los_gap = weighted_target_los - current_los

        # 추가 병상일수 계산
        additional_bed_days = los_gap * patient_count

        return {
            'doctor': doctor_name,
            'department': doctor_row.get('department', ''),
            'patient_count': patient_count,
            'total_bed_days': total_bed_days,
            'current_los': round(current_los, 2),
            'target_los': round(weighted_target_los, 2),
            'los_gap': round(los_gap, 2),
            'additional_bed_days': round(additional_bed_days, 2),
            'status': 'calculated'
        }

    # 하위 호환성 별칭
    calculate_doctor_kpi = calculate_doctor_kpi_by_diagnosis

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
                'simple_avg_current_los': 0,
                'simple_avg_target_los': 0,
                'total_additional_bed_days': 0,
                'current_utilization_rate': 0,
                'target_utilization_rate': 0,
                'patient_count': 0
            }

        # 단순 평균 재원일수 (환자수 가중치 없이)
        simple_avg_current_los = valid_kpis['current_los'].mean()
        simple_avg_target_los = valid_kpis['target_los'].mean()

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
            'simple_avg_current_los': round(simple_avg_current_los, 2),
            'simple_avg_target_los': round(simple_avg_target_los, 2),
            'total_additional_bed_days': round(total_additional_bed_days, 0),
            'current_utilization_rate': round(current_utilization_rate, 1),
            'target_utilization_rate': round(target_utilization_rate, 1),
            'patient_count': int(total_patient_count)
        }
