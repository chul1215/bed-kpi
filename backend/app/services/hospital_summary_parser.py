"""
병원별 시트 파서 - ICD-10 코드 포함 의사별 질환 집계 데이터

'25년도 대전, 유성 의사별 퇴원진단' 파일의 '병원별' 시트를 파싱합니다.
이 시트에는 의사별로 질환이 집계되어 있으며, ICD-10 코드가 포함되어 있습니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class HospitalSummaryParser:
    """병원별 시트 파서 (ICD-10 코드 포함)"""

    @staticmethod
    def parse_hospital_summary(file_path: Path | str) -> pd.DataFrame:
        """
        병원별 시트 파싱 - 의사별 질환 집계 데이터

        Args:
            file_path: 엑셀 파일 경로

        Returns:
            DataFrame with columns:
            - hospital: 병원명 (유성/대전)
            - doctor: 의사명
            - diagnosis: 진단명
            - patient_count: 환자수
            - avg_los: 평균재원일수
            - icd10_code: ICD-10 코드
        """
        try:
            # 병원별 시트 읽기 (header 없이)
            df_raw = pd.read_excel(file_path, sheet_name='병원별', header=None)

            # 유성 데이터 파싱 (컬럼 0-4)
            yuseong_data = HospitalSummaryParser._parse_hospital_column(
                df_raw, hospital='유성', col_offset=0
            )

            # 대전 데이터 파싱 (컬럼 6-10)
            daejeon_data = HospitalSummaryParser._parse_hospital_column(
                df_raw, hospital='대전', col_offset=6
            )

            # 합치기
            all_data = yuseong_data + daejeon_data
            result_df = pd.DataFrame(all_data)

            logger.info(
                f"병원별 시트 파싱 완료: {len(result_df)}건 "
                f"(유성: {len(yuseong_data)}건, 대전: {len(daejeon_data)}건)"
            )

            return result_df

        except Exception as e:
            logger.error(f"병원별 시트 파싱 실패: {e}")
            raise

    @staticmethod
    def _parse_hospital_column(
        df_raw: pd.DataFrame,
        hospital: str,
        col_offset: int
    ) -> list[dict]:
        """
        특정 병원의 데이터 파싱 (유성 또는 대전)

        Args:
            df_raw: 원본 DataFrame
            hospital: 병원명
            col_offset: 컬럼 시작 위치 (유성: 0, 대전: 6)

        Returns:
            파싱된 데이터 리스트
        """
        data = []
        current_doctor = None

        # 5번째 행부터 데이터 시작 (0-4행은 헤더)
        for i in range(5, len(df_raw)):
            row = df_raw.iloc[i]

            # 컬럼 추출
            doctor = row[col_offset]
            diagnosis = row[col_offset + 1]
            patient_count = row[col_offset + 2]
            avg_los = row[col_offset + 3]
            icd10_code = row[col_offset + 4]

            # 의사명이 있으면 업데이트
            if pd.notna(doctor) and str(doctor).strip() != '':
                current_doctor = str(doctor).strip()

            # 진단명과 환자수가 있으면 데이터 추가
            if pd.notna(diagnosis) and pd.notna(patient_count) and current_doctor:
                data.append({
                    'hospital': hospital,
                    'doctor': current_doctor,
                    'diagnosis': str(diagnosis).strip(),
                    'patient_count': int(patient_count),
                    'avg_los': float(avg_los) if pd.notna(avg_los) else 0.0,
                    'icd10_code': str(icd10_code).strip().upper() if pd.notna(icd10_code) else None
                })

        return data

    @staticmethod
    def convert_to_patient_records(summary_df: pd.DataFrame) -> pd.DataFrame:
        """
        집계 데이터를 개별 환자 레코드 형식으로 변환

        Args:
            summary_df: 집계된 데이터 (의사별 질환별)

        Returns:
            개별 환자 레코드 형식 DataFrame (기존 SMC 파일 형식과 호환)
        """
        # 환자수만큼 행을 반복하여 개별 레코드 생성
        records = []

        for _, row in summary_df.iterrows():
            patient_count = row['patient_count']

            # 환자수만큼 개별 레코드 생성
            for _ in range(patient_count):
                records.append({
                    'hospital': row['hospital'],
                    'doctor': row['doctor'],
                    'diagnosis': row['diagnosis'],
                    'los_days': row['avg_los'],  # 평균값 사용
                    'icd10_code': row['icd10_code']
                })

        result_df = pd.DataFrame(records)

        logger.info(
            f"집계 데이터 → 개별 레코드 변환: "
            f"{len(summary_df)}건 → {len(result_df)}건"
        )

        return result_df
