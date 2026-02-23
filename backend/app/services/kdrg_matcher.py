"""
KDRG 4.4 기반 DRG 매칭 서비스

KDRG 버전 4.4 분류집을 사용하여 SMC 진단명과 HIRA ADRG를 매칭합니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class KDRGMatcher:
    """KDRG 4.4 기반 DRG 매칭 클래스"""

    def __init__(self):
        self.kdrg_df: pd.DataFrame | None = None
        self.kdrg_adrg_map: Dict[str, str] = {}  # ADRG코드 → 질병군명칭
        self.diagnosis_to_adrg: Dict[str, str] = {}  # 수동 매핑: 진단명 → ADRG명
        self.icd10_to_adrg: Dict[str, str] = {}  # ICD-10 코드 → ADRG코드 매핑 (KDRG 4.6)
        self.adrg_code_to_hira: Dict[str, float] = {}  # ADRG코드 → 목표 LOS
        self.adrg_to_hira: Dict[str, float] = {}  # ADRG명 → 목표 LOS

    def load_kdrg_table(self, file_path: Path | str) -> None:
        """
        KDRG 4.4 질병군명칭 테이블 로드

        Args:
            file_path: KDRG 버전4.4_질병군명칭_20221101(변동없음).xlsx 경로
        """
        try:
            self.kdrg_df = pd.read_excel(file_path)

            # ADRG 레벨만 추출 (중증도 제거)
            kdrg_adrg = self.kdrg_df.drop_duplicates(subset=['ADRG'])[['ADRG', '질병군 명칭']]

            # ADRG 코드 → 질병군명칭 매핑
            self.kdrg_adrg_map = dict(zip(kdrg_adrg['ADRG'], kdrg_adrg['질병군 명칭']))

            logger.info(f"KDRG 4.4 로드 완료: {len(self.kdrg_adrg_map)}개 ADRG")

        except Exception as e:
            logger.error(f"KDRG 4.4 로드 실패: {e}")
            raise

    def load_manual_mapping(self, file_path: Path | str) -> None:
        """
        수동 매핑 테이블 로드 (진단명 → ADRG명)

        Args:
            file_path: 수동 매핑 엑셀 파일 경로
        """
        try:
            if not Path(file_path).exists():
                logger.warning(f"수동 매핑 파일 없음: {file_path}")
                return

            mapping_df = pd.read_excel(file_path)

            # 필수 컬럼 확인
            if 'diagnosis' not in mapping_df.columns or 'adrg_name' not in mapping_df.columns:
                logger.error("수동 매핑 파일에 'diagnosis', 'adrg_name' 컬럼 필요")
                return

            # 진단명 → ADRG명 매핑
            for _, row in mapping_df.iterrows():
                diagnosis = str(row['diagnosis']).strip()
                adrg_name = str(row['adrg_name']).strip()

                if pd.notna(diagnosis) and pd.notna(adrg_name):
                    self.diagnosis_to_adrg[diagnosis] = adrg_name

            logger.info(f"수동 매핑 로드: {len(self.diagnosis_to_adrg)}개")

        except Exception as e:
            logger.error(f"수동 매핑 로드 실패: {e}")
            raise

    def load_icd10_mapping(self, file_path: Path | str) -> None:
        """
        ICD-10 → ADRG 매핑 테이블 로드 (KDRG 4.6)

        Args:
            file_path: ICD-10 매핑 엑셀 파일 경로 (icd10_to_adrg_from_kdrg46.xlsx)
        """
        try:
            if not Path(file_path).exists():
                logger.warning(f"ICD-10 매핑 파일 없음: {file_path}")
                return

            mapping_df = pd.read_excel(file_path)

            # 필수 컬럼 확인
            if 'icd10_code' not in mapping_df.columns or 'adrg_code' not in mapping_df.columns:
                logger.error("ICD-10 매핑 파일에 'icd10_code', 'adrg_code' 컬럼 필요")
                return

            # ICD-10 코드 → ADRG 코드 매핑
            for _, row in mapping_df.iterrows():
                icd10_code = str(row['icd10_code']).strip()
                adrg_code = str(row['adrg_code']).strip()

                if pd.notna(icd10_code) and pd.notna(adrg_code):
                    self.icd10_to_adrg[icd10_code] = adrg_code

            logger.info(f"ICD-10 매핑 로드: {len(self.icd10_to_adrg)}개")

        except Exception as e:
            logger.error(f"ICD-10 매핑 로드 실패: {e}")
            raise

    def match_smc_to_hira(
        self,
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        SMC 진단명과 HIRA ADRG 매칭

        매칭 전략 (우선순위):
        1. ICD-10 코드 매칭 (KDRG 4.6 기반) ⭐ 신규
        2. 수동 매핑 테이블 (진단명 → ADRG명)
        3. 진단명과 ADRG명 직접 일치
        4. 진단명이 ADRG명에 포함 (부분 일치)
        5. ADRG명이 진단명에 포함 (부분 일치)

        Args:
            smc_df: SMC 데이터프레임 (icd10_code 컬럼 포함 시 우선 사용)
            hira_df: HIRA 데이터프레임

        Returns:
            (매칭된 SMC 데이터프레임, 진단명→목표LOS 매핑 딕셔너리)
        """
        # HIRA ADRG명 → 목표 LOS 매핑
        self.adrg_to_hira = dict(zip(hira_df['adrg_name'], hira_df['target_los']))

        # HIRA ADRG코드 → 목표 LOS 매핑 (4단DRG번호 3자리 추출)
        if 'adrg_code' in hira_df.columns:
            self.adrg_code_to_hira = dict(zip(hira_df['adrg_code'], hira_df['target_los']))
        else:
            # 4단DRG번호에서 ADRG 코드 추출 (앞 3자리)
            hira_df['adrg_code'] = hira_df['drg_code'].astype(str).str[:3]
            self.adrg_code_to_hira = dict(zip(hira_df['adrg_code'], hira_df['target_los']))

        # 매칭 결과 저장
        disease_target_map = {}

        # SMC 고유 진단명
        unique_diagnoses = smc_df['diagnosis'].unique()

        # ICD-10 기반 매칭 통계
        icd10_matched = 0
        diagnosis_matched = 0

        for diagnosis in unique_diagnoses:
            # ICD-10 코드가 있으면 우선 사용
            if 'icd10_code' in smc_df.columns:
                # 해당 진단명의 ICD-10 코드 조회
                icd10_codes = smc_df[smc_df['diagnosis'] == diagnosis]['icd10_code'].unique()
                if len(icd10_codes) > 0 and pd.notna(icd10_codes[0]):
                    icd10_code = str(icd10_codes[0]).strip()
                    target_los = self.get_target_los_by_icd10(icd10_code)
                    if target_los is not None:
                        disease_target_map[diagnosis] = target_los
                        icd10_matched += 1
                        continue

            # ICD-10 매칭 실패 시 진단명 기반 매칭
            target_los = self.get_target_los_by_diagnosis(diagnosis)
            if target_los is not None:
                disease_target_map[diagnosis] = target_los
                diagnosis_matched += 1

        total_matched = icd10_matched + diagnosis_matched
        logger.info(
            f"매칭 완료: {total_matched}/{len(unique_diagnoses)} "
            f"({total_matched/len(unique_diagnoses)*100:.1f}%)"
        )
        if icd10_matched > 0:
            logger.info(f"  - ICD-10 기반: {icd10_matched}개")
        if diagnosis_matched > 0:
            logger.info(f"  - 진단명 기반: {diagnosis_matched}개")

        # SMC 데이터프레임에 target_los 추가
        smc_matched = smc_df.copy()
        smc_matched['target_los'] = smc_matched['diagnosis'].map(disease_target_map)

        return smc_matched, disease_target_map

    def get_target_los_by_icd10(self, icd10_code: str) -> float | None:
        """
        ICD-10 코드로 목표 LOS 조회 (KDRG 4.6 기반)

        Args:
            icd10_code: ICD-10 코드 (예: I63, K80, M17)

        Returns:
            목표 LOS (매칭 실패 시 None)
        """
        icd10_code = str(icd10_code).strip()

        # ICD-10 → ADRG 코드 매핑
        if icd10_code in self.icd10_to_adrg:
            adrg_code = self.icd10_to_adrg[icd10_code]  # 예: B011, B012

            # ADRG 코드 → 목표 LOS (정확한 매칭 우선)
            if adrg_code in self.adrg_code_to_hira:
                return self.adrg_code_to_hira[adrg_code]

            # 앞 3자리로 재시도 (HIRA는 B01, KDRG 4.6은 B011)
            if len(adrg_code) >= 3:
                adrg_code_3 = adrg_code[:3]
                if adrg_code_3 in self.adrg_code_to_hira:
                    return self.adrg_code_to_hira[adrg_code_3]

        return None

    def get_target_los_by_diagnosis(self, diagnosis: str) -> float | None:
        """
        진단명으로 목표 LOS 조회 (기존 방식)

        Args:
            diagnosis: 진단명

        Returns:
            목표 LOS (매칭 실패 시 None)
        """
        diagnosis = str(diagnosis).strip()

        # 1. 수동 매핑 테이블
        if diagnosis in self.diagnosis_to_adrg:
            adrg_name = self.diagnosis_to_adrg[diagnosis]
            if adrg_name in self.adrg_to_hira:
                return self.adrg_to_hira[adrg_name]

        # 2. 직접 일치 (진단명 = ADRG명)
        if diagnosis in self.adrg_to_hira:
            return self.adrg_to_hira[diagnosis]

        # 3. 부분 일치 (진단명 in ADRG명 or ADRG명 in 진단명)
        for adrg_name, target_los in self.adrg_to_hira.items():
            # NaN 값 체크 (HIRA 파일에 NaN이 있을 수 있음)
            if not isinstance(adrg_name, str):
                continue
            if diagnosis in adrg_name or adrg_name in diagnosis:
                return target_los

        return None

    def get_target_los(self, diagnosis: str) -> float | None:
        """
        진단명에 대한 목표 LOS 조회 (하위 호환성 유지)

        Args:
            diagnosis: 진단명

        Returns:
            목표 LOS (매칭 실패 시 None)
        """
        return self.get_target_los_by_diagnosis(diagnosis)

    def generate_mapping_template(
        self,
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame,
        output_file: Path | str,
        top_n: int = 100
    ) -> None:
        """
        매핑 템플릿 생성 (상위 N개 진단명 + 제안 ADRG)

        Args:
            smc_df: SMC 데이터프레임
            hira_df: HIRA 데이터프레임
            output_file: 출력 파일 경로
            top_n: 상위 진단명 개수
        """
        # 진단명별 환자수 집계
        diagnosis_counts = smc_df['diagnosis'].value_counts().head(top_n).reset_index()
        diagnosis_counts.columns = ['diagnosis', 'patient_count']

        # 각 진단명에 대한 제안 ADRG 찾기
        suggestions = []
        for _, row in diagnosis_counts.iterrows():
            diagnosis = row['diagnosis']
            patient_count = row['patient_count']

            # 부분 일치로 제안 찾기
            suggested_adrgs = []
            for adrg_name in self.adrg_to_hira.keys():
                if diagnosis in adrg_name or adrg_name in diagnosis:
                    suggested_adrgs.append(adrg_name)

            suggestion = suggested_adrgs[0] if suggested_adrgs else ''

            suggestions.append({
                'diagnosis': diagnosis,
                'patient_count': patient_count,
                'suggested_adrg': suggestion,
                'adrg_name': '',  # 수동 입력용
            })

        # 엑셀 파일로 저장
        template_df = pd.DataFrame(suggestions)

        # ADRG 목록 시트
        adrg_list = pd.DataFrame([
            {'adrg_name': name, 'target_los': los}
            for name, los in self.adrg_to_hira.items()
        ])

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            template_df.to_excel(writer, sheet_name='매핑템플릿', index=False)
            adrg_list.to_excel(writer, sheet_name='ADRG목록', index=False)

        logger.info(f"매핑 템플릿 생성: {output_file}")
