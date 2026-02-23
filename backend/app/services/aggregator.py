"""
데이터 집계 서비스

질환/의료진/진료과 단위로 데이터를 집계합니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from typing import Dict, List, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


class Aggregator:
    """데이터 집계 클래스"""

    @staticmethod
    def aggregate_by_adrg(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        ADRG 코드 단위 집계

        Args:
            df: SMC 파싱된 데이터프레임 (adrg_code, period 컬럼 포함)
            hospital: 병원 필터 ('대전', '유성' 또는 None)
            period: 기간 필터 ('off_season', 'normal' 또는 None)

        Returns:
            ADRG별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # ADRG 코드가 없는 행 제외
        filtered_df = filtered_df[filtered_df['adrg_code'].notna()]

        # ADRG별 집계
        agg_df = filtered_df.groupby('adrg_code').agg({
            'los_days': 'sum',          # 병상일수 합계
            'discharge_date': 'count',  # 환자수 (레코드 수)
            'hospital': 'first',        # 병원명
            'adrg_name': 'first',       # ADRG명
            'target_los': 'first'       # 목표 LOS (심평원 기준)
        }).reset_index()

        agg_df.columns = ['adrg_code', 'total_bed_days', 'patient_count', 'hospital', 'adrg_name', 'target_los']

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        # 정렬
        agg_df = agg_df.sort_values('patient_count', ascending=False)

        logger.info(f"ADRG 집계 완료: {len(agg_df)}개 ADRG, {agg_df['patient_count'].sum()}명")

        return agg_df

    @staticmethod
    def aggregate_by_diagnosis(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        진단명 단위 집계 (하위 호환성 유지)

        NOTE: ADRG 기반 집계 사용 권장. 이 함수는 레거시 지원용입니다.

        Args:
            df: SMC 파싱된 데이터프레임 (period 컬럼 포함)
            hospital: 병원 필터 ('대전', '유성' 또는 None)
            period: 기간 필터 ('off_season', 'normal' 또는 None)

        Returns:
            진단명별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # 진단명별 집계
        agg_df = filtered_df.groupby('diagnosis').agg({
            'los_days': 'sum',          # 병상일수 합계
            'discharge_date': 'count',  # 환자수 (레코드 수)
            'hospital': 'first',        # 병원명
            'target_los': 'first'       # 목표 LOS
        }).reset_index()

        agg_df.columns = ['diagnosis', 'total_bed_days', 'patient_count', 'hospital', 'target_los']

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        # 정렬
        agg_df = agg_df.sort_values('patient_count', ascending=False)

        logger.info(f"진단명 집계 완료: {len(agg_df)}개 진단명, {agg_df['patient_count'].sum()}명")

        return agg_df

    # 하위 호환성 별칭
    aggregate_by_disease = aggregate_by_diagnosis

    @staticmethod
    def aggregate_by_doctor(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        의료진 단위 집계

        Args:
            df: SMC 파싱된 데이터프레임 (period 컬럼 포함)
            hospital: 병원 필터
            period: 기간 필터

        Returns:
            의료진별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # 의료진별 집계 (진료과 통합 - 의사가 진단한 모든 진단명 기준)
        agg_df = filtered_df.groupby(['doctor', 'hospital']).agg({
            'los_days': 'sum',          # 병상일수 합계
            'discharge_date': 'count',  # 환자수
            'department': lambda x: ', '.join(sorted(x.unique()))  # 모든 진료과 표시
        }).reset_index()

        agg_df.columns = ['doctor', 'hospital', 'total_bed_days', 'patient_count', 'department']

        # 김원형 진료과를 SC로 수동 설정
        agg_df.loc[agg_df['doctor'] == '김원형', 'department'] = 'SC'

        # department 컬럼을 올바른 위치로 이동 (doctor, department, hospital 순서 유지)
        agg_df = agg_df[['doctor', 'department', 'hospital', 'total_bed_days', 'patient_count']]

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        # 정렬
        agg_df = agg_df.sort_values('patient_count', ascending=False)

        logger.info(f"의료진 집계 완료: {len(agg_df)}명, {agg_df['patient_count'].sum()}명")

        return agg_df

    @staticmethod
    def aggregate_by_department(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        진료과 단위 집계

        Args:
            df: SMC 파싱된 데이터프레임 (period 컬럼 포함)
            hospital: 병원 필터
            period: 기간 필터

        Returns:
            진료과별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # 진료과별 집계
        agg_df = filtered_df.groupby(['department', 'hospital']).agg({
            'los_days': 'sum',          # 병상일수 합계
            'discharge_date': 'count'   # 환자수
        }).reset_index()

        agg_df.columns = ['department', 'hospital', 'total_bed_days', 'patient_count']

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        # 정렬
        agg_df = agg_df.sort_values('patient_count', ascending=False)

        logger.info(f"진료과 집계 완료: {len(agg_df)}개 과, {agg_df['patient_count'].sum()}명")

        return agg_df

    @staticmethod
    def aggregate_by_doctor_adrg(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        의료진-ADRG 단위 집계 (의사별 ADRG TOP 6용)

        Args:
            df: SMC 파싱된 데이터프레임 (adrg_code 컬럼 포함)
            hospital: 병원 필터
            period: 기간 필터

        Returns:
            의료진-ADRG별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # ADRG 코드가 없는 행 제외
        filtered_df = filtered_df[filtered_df['adrg_code'].notna()]

        # 의료진-ADRG별 집계
        agg_df = filtered_df.groupby(['doctor', 'department', 'adrg_code', 'hospital']).agg({
            'los_days': 'sum',
            'discharge_date': 'count',
            'adrg_name': 'first',
            'target_los': 'first'
        }).reset_index()

        agg_df.columns = [
            'doctor', 'department', 'adrg_code', 'hospital',
            'total_bed_days', 'patient_count', 'adrg_name', 'target_los'
        ]

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        logger.info(f"의료진-ADRG 집계 완료: {len(agg_df)}개 조합")

        return agg_df

    @staticmethod
    def aggregate_by_doctor_diagnosis(
        df: pd.DataFrame,
        hospital: str = None,
        period: str = None
    ) -> pd.DataFrame:
        """
        의료진-진단명 단위 집계 (하위 호환성 유지)

        NOTE: ADRG 기반 집계 사용 권장. 이 함수는 레거시 지원용입니다.

        Args:
            df: SMC 파싱된 데이터프레임
            hospital: 병원 필터
            period: 기간 필터

        Returns:
            의료진-진단명별 집계 데이터프레임
        """
        filtered_df = df.copy()

        # 필터링
        if hospital:
            filtered_df = filtered_df[filtered_df['hospital'] == hospital]
        if period:
            filtered_df = filtered_df[filtered_df['period'] == period]

        # 의료진-진단명별 집계
        agg_df = filtered_df.groupby(['doctor', 'department', 'diagnosis', 'hospital']).agg({
            'los_days': 'sum',
            'discharge_date': 'count'
        }).reset_index()

        agg_df.columns = ['doctor', 'department', 'diagnosis', 'hospital', 'total_bed_days', 'patient_count']

        # 현재 LOS 계산
        agg_df['current_los'] = agg_df['total_bed_days'] / agg_df['patient_count']

        logger.info(f"의료진-진단명 집계 완료: {len(agg_df)}개 조합")

        return agg_df

    # 하위 호환성 별칭
    aggregate_by_doctor_disease = aggregate_by_doctor_diagnosis

    @staticmethod
    def get_doctor_top_adrgs(
        doctor_adrg_df: pd.DataFrame,
        doctor_name: str,
        top_n: int = 6
    ) -> pd.DataFrame:
        """
        의료진의 ADRG TOP N 추출

        Args:
            doctor_adrg_df: 의료진-ADRG 집계 데이터
            doctor_name: 의료진명
            top_n: 상위 개수 (기본값: 6)

        Returns:
            의료진의 ADRG TOP N (환자수 기준)
        """
        doctor_df = doctor_adrg_df[doctor_adrg_df['doctor'] == doctor_name].copy()
        top_adrgs = doctor_df.nlargest(top_n, 'patient_count')

        return top_adrgs

    @staticmethod
    def get_doctor_top_diseases(
        doctor_disease_df: pd.DataFrame,
        doctor_name: str,
        top_n: int = 6
    ) -> pd.DataFrame:
        """
        의료진의 진단명 TOP N 추출 (하위 호환성 유지)

        NOTE: get_doctor_top_adrgs 사용 권장

        Args:
            doctor_disease_df: 의료진-진단명 집계 데이터
            doctor_name: 의료진명
            top_n: 상위 개수 (기본값: 6)

        Returns:
            의료진의 진단명 TOP N (환자수 기준)
        """
        doctor_df = doctor_disease_df[doctor_disease_df['doctor'] == doctor_name].copy()
        top_diseases = doctor_df.nlargest(top_n, 'patient_count')

        return top_diseases

    @staticmethod
    def calculate_consistency_error(
        disease_agg: pd.DataFrame,
        doctor_agg: pd.DataFrame,
        department_agg: pd.DataFrame
    ) -> Dict[str, any]:
        """
        데이터 정합성 검증

        진료과 합계 = 의료진 합계 = 전체 합계 확인

        Args:
            disease_agg: 질환별 집계
            doctor_agg: 의료진별 집계
            department_agg: 진료과별 집계

        Returns:
            검증 결과 딕셔너리
        """
        disease_total_patients = disease_agg['patient_count'].sum()
        disease_total_bed_days = disease_agg['total_bed_days'].sum()

        doctor_total_patients = doctor_agg['patient_count'].sum()
        doctor_total_bed_days = doctor_agg['total_bed_days'].sum()

        department_total_patients = department_agg['patient_count'].sum()
        department_total_bed_days = department_agg['total_bed_days'].sum()

        errors = {
            'disease_doctor_patients': abs(disease_total_patients - doctor_total_patients),
            'disease_department_patients': abs(disease_total_patients - department_total_patients),
            'disease_doctor_bed_days': abs(disease_total_bed_days - doctor_total_bed_days),
            'disease_department_bed_days': abs(disease_total_bed_days - department_total_bed_days),
            'is_consistent': (
                disease_total_patients == doctor_total_patients == department_total_patients and
                disease_total_bed_days == doctor_total_bed_days == department_total_bed_days
            )
        }

        if errors['is_consistent']:
            logger.info("✅ 데이터 정합성 검증 통과")
        else:
            logger.warning(f"⚠️ 정합성 오류 감지: {errors}")

        return errors
