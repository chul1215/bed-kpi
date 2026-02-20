"""
DRG 매칭 서비스

SMC 진단명과 HIRA DRG 코드를 매칭합니다.
"""
from __future__ import annotations

import pandas as pd
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class DRGMatcher:
    """DRG 매칭 클래스"""

    def __init__(self, mapping_file: Path | str = None):
        """
        초기화

        Args:
            mapping_file: DRG 매핑 파일 경로
        """
        self.mapping_file = Path(mapping_file or settings.DRG_MAPPING_FILE)
        self.mapping_df = None
        self._load_mapping()

    def _load_mapping(self) -> None:
        """매핑 테이블 로드"""
        if not self.mapping_file.exists():
            logger.warning(
                f"DRG 매핑 파일이 없습니다: {self.mapping_file}\n"
                f"초기 매핑 테이블을 먼저 생성해주세요."
            )
            self.mapping_df = pd.DataFrame(columns=[
                'diagnosis', 'drg_code_3digit', 'adrg_name', 'confidence'
            ])
            return

        try:
            self.mapping_df = pd.read_excel(self.mapping_file)
            logger.info(
                f"DRG 매핑 테이블 로드 완료: {len(self.mapping_df)}개 항목"
            )
        except Exception as e:
            logger.error(f"DRG 매핑 파일 로드 오류: {e}")
            self.mapping_df = pd.DataFrame(columns=[
                'diagnosis', 'drg_code_3digit', 'adrg_name', 'confidence'
            ])

    def get_target_los(
        self,
        diagnosis: str,
        hira_df: pd.DataFrame
    ) -> float | None:
        """
        진단명으로 목표 LOS 조회

        Args:
            diagnosis: 진단명
            hira_df: HIRA 데이터프레임

        Returns:
            목표 LOS 또는 None
        """
        # 매핑 테이블에서 DRG 코드 조회
        if self.mapping_df.empty:
            return None

        mapping_row = self.mapping_df[
            self.mapping_df['diagnosis'] == diagnosis
        ]

        if mapping_row.empty:
            logger.debug(f"매핑 테이블에 없음: {diagnosis}")
            return None

        drg_code_3digit = mapping_row.iloc[0]['drg_code_3digit']

        # HIRA 데이터에서 목표 LOS 조회
        hira_row = hira_df[
            hira_df['drg_code_3digit'] == str(drg_code_3digit)
        ]

        if hira_row.empty:
            logger.debug(f"HIRA에 없음: DRG {drg_code_3digit}")
            return None

        # 첫 번째 매칭 행 반환 (여러 개인 경우)
        target_los = hira_row.iloc[0]['target_los']

        return float(target_los)

    def match_all_diagnoses(
        self,
        diagnoses: list[str],
        hira_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        모든 진단명에 대해 목표 LOS 매칭

        Args:
            diagnoses: 진단명 리스트
            hira_df: HIRA 데이터프레임

        Returns:
            {'진단명': target_los, ...}
        """
        result = {}
        matched_count = 0
        unmatched = []

        for diagnosis in diagnoses:
            target_los = self.get_target_los(diagnosis, hira_df)
            if target_los is not None:
                result[diagnosis] = target_los
                matched_count += 1
            else:
                unmatched.append(diagnosis)

        match_rate = (matched_count / len(diagnoses) * 100) if diagnoses else 0
        logger.info(
            f"DRG 매칭 완료: {matched_count}/{len(diagnoses)} "
            f"({match_rate:.1f}%)"
        )

        if unmatched:
            logger.warning(f"매칭 실패 진단명 ({len(unmatched)}개): {unmatched[:10]}")

        return result

    @staticmethod
    def create_initial_mapping(
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame,
        output_file: Path | str
    ) -> None:
        """
        초기 매핑 테이블 생성 (수동 매핑용)

        SMC 고유 진단명 추출 → Excel로 저장
        사용자가 수동으로 매핑 후 DRG 코드 입력

        Args:
            smc_df: SMC 데이터프레임
            hira_df: HIRA 데이터프레임
            output_file: 저장 파일 경로
        """
        # 고유 진단명 추출
        unique_diagnoses = smc_df['diagnosis'].unique()
        diagnosis_counts = smc_df['diagnosis'].value_counts()

        # 매핑 템플릿 생성
        mapping_template = pd.DataFrame({
            'diagnosis': unique_diagnoses,
            'patient_count': [diagnosis_counts[d] for d in unique_diagnoses],
            'drg_code_3digit': '',  # 수동 입력
            'adrg_name': '',        # 참고용
            'confidence': 0.0       # 매칭 확신도
        })

        # 환자수 기준 내림차순 정렬
        mapping_template = mapping_template.sort_values('patient_count', ascending=False)

        # Excel 저장
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        mapping_template.to_excel(output_file, index=False)

        logger.info(
            f"초기 매핑 테이블 생성 완료: {output_file}\n"
            f"총 {len(unique_diagnoses)}개 진단명"
        )

    @staticmethod
    def get_unmatched_diagnoses(
        smc_df: pd.DataFrame,
        mapping_df: pd.DataFrame
    ) -> list[str]:
        """
        매칭되지 않은 진단명 목록

        Args:
            smc_df: SMC 데이터프레임
            mapping_df: 매핑 데이터프레임

        Returns:
            매핑 실패 진단명 리스트
        """
        smc_diagnoses = set(smc_df['diagnosis'].unique())
        mapped_diagnoses = set(mapping_df['diagnosis'].unique())

        unmatched = list(smc_diagnoses - mapped_diagnoses)

        logger.info(f"매칭 실패 진단명: {len(unmatched)}개")

        return sorted(unmatched)
