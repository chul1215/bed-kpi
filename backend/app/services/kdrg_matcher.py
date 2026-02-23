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

    def match_smc_to_hira(
        self,
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        SMC 진단명과 HIRA ADRG 매칭

        매칭 전략:
        1. 수동 매핑 테이블 우선
        2. 진단명과 ADRG명 직접 일치
        3. 진단명이 ADRG명에 포함 (부분 일치)
        4. ADRG명이 진단명에 포함 (부분 일치)

        Args:
            smc_df: SMC 데이터프레임
            hira_df: HIRA 데이터프레임

        Returns:
            (매칭된 SMC 데이터프레임, 진단명→목표LOS 매핑 딕셔너리)
        """
        # HIRA ADRG명 → 목표 LOS 매핑
        self.adrg_to_hira = dict(zip(hira_df['adrg_name'], hira_df['target_los']))

        # 매칭 결과 저장
        disease_target_map = {}

        # SMC 고유 진단명
        unique_diagnoses = smc_df['diagnosis'].unique()

        matched_count = 0
        for diagnosis in unique_diagnoses:
            target_los = self.get_target_los(diagnosis)
            if target_los is not None:
                disease_target_map[diagnosis] = target_los
                matched_count += 1

        logger.info(
            f"매칭 완료: {matched_count}/{len(unique_diagnoses)} "
            f"({matched_count/len(unique_diagnoses)*100:.1f}%)"
        )

        # SMC 데이터프레임에 target_los 추가
        smc_matched = smc_df.copy()
        smc_matched['target_los'] = smc_matched['diagnosis'].map(disease_target_map)

        return smc_matched, disease_target_map

    def get_target_los(self, diagnosis: str) -> float | None:
        """
        진단명에 대한 목표 LOS 조회

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
            if diagnosis in adrg_name or adrg_name in diagnosis:
                return target_los

        return None

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
