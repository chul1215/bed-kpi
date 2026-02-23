"""
ADRG 코드 매핑 서비스
- HIRA ADRG 코드를 기준으로 SMC 진단명을 매핑
- ICD-10 기반 자동 매핑 + 수동 매핑 지원
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ADRGMapper:
    """ADRG 코드 매핑 서비스"""

    def __init__(self):
        self.adrg_to_target_los: Dict[str, float] = {}  # ADRG 코드 → 목표 LOS
        self.adrg_to_name: Dict[str, str] = {}  # ADRG 코드 → ADRG명
        self.icd10_to_adrg: Dict[str, str] = {}  # ICD-10 → ADRG 코드
        self.diagnosis_to_adrg: Dict[str, str] = {}  # 진단명 → ADRG 코드

    def load_hira_adrg_table(self, file_path: str | Path) -> pd.DataFrame:
        """
        HIRA ADRG 테이블 로드

        Returns:
            DataFrame with columns: adrg_code, adrg_name, target_los
        """
        df = pd.read_excel(file_path, skiprows=2, header=0)

        # $ 행 제거
        df = df[df['4단DRG번호'] != '$'].copy()

        # 마지막 타임스탬프 행 제거
        df = df.dropna(subset=['4단DRG번호', 'ADRG명', '평균재원일수'])

        # 컬럼 정규화
        df = df.rename(columns={
            '4단DRG번호': 'adrg_code',
            'ADRG명': 'adrg_name',
            '평균재원일수': 'target_los'
        })

        # ADRG 코드 문자열로 변환 (4자리 패딩)
        df['adrg_code'] = df['adrg_code'].astype(str).str.strip()

        # 딕셔너리 저장
        self.adrg_to_target_los = dict(zip(df['adrg_code'], df['target_los']))
        self.adrg_to_name = dict(zip(df['adrg_code'], df['adrg_name']))

        logger.info(f"HIRA ADRG 테이블 로드 완료: {len(df)}개 ADRG")
        return df[['adrg_code', 'adrg_name', 'target_los']]

    def load_icd10_to_adrg_mapping(self, file_path: str | Path) -> None:
        """
        ICD-10 → ADRG 자동 매핑 로드

        파일 구조:
        - icd10_code: ICD-10 코드 (예: A00)
        - adrg_code: ADRG 코드 (예: C010)
        """
        try:
            df = pd.read_excel(file_path)

            if 'icd10_code' not in df.columns or 'adrg_code' not in df.columns:
                logger.warning(f"ICD-10 매핑 파일에 필수 컬럼 없음: {file_path}")
                return

            # NaN 제거
            df = df.dropna(subset=['icd10_code', 'adrg_code'])

            # 문자열로 변환
            df['icd10_code'] = df['icd10_code'].astype(str).str.strip().str.upper()
            df['adrg_code'] = df['adrg_code'].astype(str).str.strip()

            # 딕셔너리 저장
            self.icd10_to_adrg = dict(zip(df['icd10_code'], df['adrg_code']))

            logger.info(f"ICD-10 → ADRG 매핑 로드: {len(self.icd10_to_adrg)}개")
        except Exception as e:
            logger.warning(f"ICD-10 매핑 파일 로드 실패: {e}")

    def load_manual_diagnosis_mapping(self, file_path: str | Path) -> None:
        """
        진단명 → ADRG 수동 매핑 로드

        파일 구조:
        - diagnosis: SMC 진단명
        - adrg_code: ADRG 코드
        """
        try:
            df = pd.read_excel(file_path)

            if 'diagnosis' not in df.columns or 'adrg_code' not in df.columns:
                logger.warning(f"진단명 매핑 파일에 필수 컬럼 없음: {file_path}")
                return

            # NaN 제거
            df = df.dropna(subset=['diagnosis', 'adrg_code'])

            # 문자열로 변환
            df['diagnosis'] = df['diagnosis'].astype(str).str.strip()
            df['adrg_code'] = df['adrg_code'].astype(str).str.strip()

            # 딕셔너리 저장
            self.diagnosis_to_adrg = dict(zip(df['diagnosis'], df['adrg_code']))

            logger.info(f"진단명 → ADRG 매핑 로드: {len(self.diagnosis_to_adrg)}개")
        except Exception as e:
            logger.warning(f"진단명 매핑 파일 로드 실패: {e}")

    def get_adrg_code(
        self,
        diagnosis: str,
        icd10_code: Optional[str] = None
    ) -> Optional[str]:
        """
        진단명과 ICD-10 코드로 ADRG 코드 조회

        우선순위:
        1. ICD-10 자동 매핑
        2. 진단명 수동 매핑
        3. 진단명 직접 일치 (ADRG명과 동일)
        4. 진단명 부분 일치 (ADRG명에 포함)

        Args:
            diagnosis: SMC 진단명
            icd10_code: ICD-10 코드 (선택)

        Returns:
            ADRG 코드 또는 None
        """
        diagnosis = str(diagnosis).strip()

        # 1. ICD-10 자동 매핑 (우선순위 최상)
        if icd10_code:
            icd10_code = str(icd10_code).strip().upper()
            if icd10_code in self.icd10_to_adrg:
                return self.icd10_to_adrg[icd10_code]

        # 2. 진단명 수동 매핑
        if diagnosis in self.diagnosis_to_adrg:
            return self.diagnosis_to_adrg[diagnosis]

        # 3. 진단명 직접 일치 (ADRG명과 동일)
        for adrg_code, adrg_name in self.adrg_to_name.items():
            if diagnosis == adrg_name:
                return adrg_code

        # 4. 진단명 부분 일치
        for adrg_code, adrg_name in self.adrg_to_name.items():
            if diagnosis in adrg_name or adrg_name in diagnosis:
                return adrg_code

        return None

    def get_target_los(self, adrg_code: str) -> Optional[float]:
        """ADRG 코드로 목표 LOS 조회"""
        adrg_code = str(adrg_code).strip()
        return self.adrg_to_target_los.get(adrg_code)

    def get_adrg_name(self, adrg_code: str) -> Optional[str]:
        """ADRG 코드로 ADRG명 조회"""
        adrg_code = str(adrg_code).strip()
        return self.adrg_to_name.get(adrg_code)

    def add_adrg_to_smc(
        self,
        smc_df: pd.DataFrame,
        icd10_column: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Tuple[str, float]]]:
        """
        SMC 데이터에 ADRG 코드 추가

        Args:
            smc_df: SMC 원본 데이터
            icd10_column: ICD-10 컬럼명 (있는 경우)

        Returns:
            (ADRG 추가된 DataFrame, adrg_info_map)
            adrg_info_map: {adrg_code: (adrg_name, target_los)}
        """
        df = smc_df.copy()

        # ADRG 코드 매핑
        if icd10_column and icd10_column in df.columns:
            df['adrg_code'] = df.apply(
                lambda row: self.get_adrg_code(
                    row['diagnosis'],
                    row.get(icd10_column)
                ),
                axis=1
            )
        else:
            df['adrg_code'] = df['diagnosis'].apply(
                lambda d: self.get_adrg_code(d, None)
            )

        # ADRG명과 목표 LOS 추가
        df['adrg_name'] = df['adrg_code'].apply(
            lambda c: self.get_adrg_name(c) if pd.notna(c) else None
        )
        df['target_los'] = df['adrg_code'].apply(
            lambda c: self.get_target_los(c) if pd.notna(c) else None
        )

        # 매칭 통계
        total = len(df)
        matched = df['adrg_code'].notna().sum()
        match_rate = matched / total * 100 if total > 0 else 0

        logger.info(f"ADRG 매칭 완료: {matched}/{total} ({match_rate:.1f}%)")

        # ADRG 정보 딕셔너리 생성 (NaN 제거)
        adrg_info_map = {}
        for _, row in df[df['adrg_code'].notna()].iterrows():
            adrg_code = row['adrg_code']
            if adrg_code not in adrg_info_map:
                adrg_info_map[adrg_code] = (
                    row['adrg_name'],
                    row['target_los']
                )

        return df, adrg_info_map

    def generate_mapping_template(
        self,
        smc_df: pd.DataFrame,
        output_file: str | Path,
        top_n: int = 100
    ) -> None:
        """
        미매칭 진단명 TOP N 매핑 템플릿 생성

        Args:
            smc_df: ADRG 추가된 SMC 데이터
            output_file: 출력 파일 경로
            top_n: 상위 N개 진단명
        """
        # 미매칭 진단명 집계
        unmatched = smc_df[smc_df['adrg_code'].isna()].copy()

        if len(unmatched) == 0:
            logger.info("미매칭 진단명 없음")
            return

        diagnosis_counts = unmatched['diagnosis'].value_counts().head(top_n)

        # 템플릿 생성
        template_df = pd.DataFrame({
            'diagnosis': diagnosis_counts.index,
            'patient_count': diagnosis_counts.values,
            'adrg_code': '',
            'suggested_adrg_name': ''
        })

        # ADRG 목록 시트 추가
        adrg_list_df = pd.DataFrame({
            'adrg_code': list(self.adrg_to_name.keys()),
            'adrg_name': list(self.adrg_to_name.values()),
            'target_los': [self.adrg_to_target_los.get(c) for c in self.adrg_to_name.keys()]
        })

        with pd.ExcelWriter(output_file) as writer:
            template_df.to_excel(writer, sheet_name='미매칭_진단명', index=False)
            adrg_list_df.to_excel(writer, sheet_name='ADRG_목록', index=False)

        logger.info(f"매핑 템플릿 생성: {output_file} (상위 {top_n}개)")
