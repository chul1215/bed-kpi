"""
DRG 매칭 서비스 (ADRG 코드 + 진단명 하이브리드)

매칭 전략:
1. ADRG 코드 직접 매칭 (SMC ADRG → HIRA ADRG 3자리) - 최우선
2. 진단명 수동 매핑 (diagnosis_kdrg44_mapping.xlsx)
3. 진단명 자동 매칭 (부분 일치)
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class DRGMatcher:
    """ADRG 코드 + 진단명 하이브리드 DRG 매칭 클래스"""

    def __init__(self, kdrg_file: Path | str = None):
        """
        초기화

        Args:
            kdrg_file: KDRG v4.6 전체코드.xlsx 파일 경로 (선택사항)
        """
        self.kdrg_file = Path(kdrg_file) if kdrg_file else None
        self.diagnosis_to_adrg: Dict[str, str] = {}
        self.adrg_to_hira: Dict[str, float] = {}
        self.adrg_code_to_los: Dict[str, float] = {}  # ADRG 3자리 → LOS

        # KDRG 파일이 있으면 ADRG명 로드
        if self.kdrg_file and self.kdrg_file.exists():
            self._load_kdrg_adrg_names()

    def _load_kdrg_adrg_names(self) -> None:
        """KDRG ADRG 전체목록 로드 (참고용)"""
        try:
            df_adrg = pd.read_excel(
                self.kdrg_file,
                sheet_name='ADRG_전체목록'
            )
            logger.info(
                f"KDRG ADRG 목록 로드 완료: "
                f"{len(df_adrg)}개 ADRG"
            )
        except Exception as e:
            logger.warning(f"KDRG ADRG 목록 로드 실패 (선택사항): {e}")

    def load_hira_adrg_los(self, hira_df: pd.DataFrame) -> None:
        """
        HIRA ADRG별 평균재원일수 로드

        Args:
            hira_df: HIRA 데이터프레임 (컬럼: adrg_code, adrg_name, target_los)
        """
        # ADRG명 → 평균재원일수 매핑
        for _, row in hira_df.iterrows():
            adrg_name = str(row.get('adrg_name', '')).strip()
            adrg_code = str(row.get('adrg_code', '')).strip()  # drg_code 대신 adrg_code
            target_los = row.get('target_los')

            if adrg_name and pd.notna(target_los):
                # 동일 ADRG명이 여러 개 있을 수 있으므로 평균 사용
                if adrg_name in self.adrg_to_hira:
                    # 기존 값과 평균
                    self.adrg_to_hira[adrg_name] = (
                        self.adrg_to_hira[adrg_name] + float(target_los)
                    ) / 2
                else:
                    self.adrg_to_hira[adrg_name] = float(target_los)

            # ADRG 코드 3자리 → LOS 매핑 (ADRG 코드 직접 매칭용)
            if adrg_code and pd.notna(target_los):
                adrg_3 = adrg_code[:3] if len(adrg_code) >= 3 else adrg_code
                if adrg_3 in self.adrg_code_to_los:
                    # 동일 코드 여러 개 있으면 평균
                    self.adrg_code_to_los[adrg_3] = (
                        self.adrg_code_to_los[adrg_3] + float(target_los)
                    ) / 2
                else:
                    self.adrg_code_to_los[adrg_3] = float(target_los)

        logger.info(
            f"HIRA ADRG 매핑 로드 완료: "
            f"{len(self.adrg_to_hira)}개 ADRG명, "
            f"{len(self.adrg_code_to_los)}개 ADRG 코드"
        )

    def create_diagnosis_mapping(
        self,
        smc_diagnoses: list[str],
        hira_adrg_names: list[str]
    ) -> Dict[str, str]:
        """
        진단명 자동 매칭 생성 (유사도 기반)

        Args:
            smc_diagnoses: SMC 진단명 리스트
            hira_adrg_names: HIRA ADRG명 리스트

        Returns:
            진단명 → ADRG명 매핑 딕셔너리
        """
        mapping = {}

        for diagnosis in smc_diagnoses:
            diagnosis_clean = str(diagnosis).strip()
            if not diagnosis_clean:
                continue

            # 완전 일치 우선
            if diagnosis_clean in hira_adrg_names:
                mapping[diagnosis_clean] = diagnosis_clean
                continue

            # 부분 일치 검색
            matched = False
            for adrg_name in hira_adrg_names:
                # 진단명이 ADRG명에 포함되는 경우
                if diagnosis_clean in adrg_name:
                    mapping[diagnosis_clean] = adrg_name
                    matched = True
                    break
                # ADRG명이 진단명에 포함되는 경우
                elif adrg_name in diagnosis_clean:
                    mapping[diagnosis_clean] = adrg_name
                    matched = True
                    break

        logger.info(
            f"진단명 자동 매칭 생성: "
            f"{len(mapping)}/{len(smc_diagnoses)}개 매칭됨 "
            f"({len(mapping)/len(smc_diagnoses)*100:.1f}%)"
        )

        return mapping

    def load_manual_mapping(self, mapping_file: Path | str) -> None:
        """
        수동 매핑 테이블 로드

        Args:
            mapping_file: 진단명-ADRG 매핑 엑셀 파일 경로
                         (컬럼: diagnosis, adrg_name)
        """
        mapping_path = Path(mapping_file)
        if not mapping_path.exists():
            logger.warning(f"매핑 파일이 없습니다: {mapping_file}")
            return

        try:
            df = pd.read_excel(mapping_path)
            for _, row in df.iterrows():
                diagnosis = str(row.get('diagnosis', '')).strip()
                adrg_name = str(row.get('adrg_name', '')).strip()

                if diagnosis and adrg_name:
                    self.diagnosis_to_adrg[diagnosis] = adrg_name

            logger.info(
                f"수동 매핑 테이블 로드 완료: "
                f"{len(self.diagnosis_to_adrg)}개 매핑"
            )
        except Exception as e:
            logger.error(f"매핑 테이블 로드 오류: {e}")

    def get_target_los(
        self,
        diagnosis: str,
        adrg_code: str | None = None
    ) -> float | None:
        """
        진단명 또는 ADRG 코드로 목표 LOS 조회 (하이브리드)

        Args:
            diagnosis: 진단명 (예: "폐렴", "급성 충수염")
            adrg_code: ADRG 코드 (예: "P672", 선택사항)

        Returns:
            목표 LOS 또는 None

        매칭 우선순위:
            1. ADRG 코드 직접 매칭 (가장 정확)
            2. 진단명 수동 매핑
            3. 진단명 = ADRG명 직접 일치
            4. 진단명 부분 일치
        """
        diagnosis = str(diagnosis).strip()

        # 1. ADRG 코드 직접 매칭 (최우선)
        if adrg_code and str(adrg_code) != '미매핑':
            adrg_code = str(adrg_code).strip()
            adrg_3 = adrg_code[:3] if len(adrg_code) >= 3 else adrg_code
            if adrg_3 in self.adrg_code_to_los:
                return self.adrg_code_to_los[adrg_3]

        # 2. 수동 매핑 테이블에서 찾기
        if diagnosis in self.diagnosis_to_adrg:
            adrg_name = self.diagnosis_to_adrg[diagnosis]
            if adrg_name in self.adrg_to_hira:
                return self.adrg_to_hira[adrg_name]

        # 3. 직접 ADRG명으로 찾기 (진단명 = ADRG명)
        if diagnosis in self.adrg_to_hira:
            return self.adrg_to_hira[diagnosis]

        # 4. 부분 일치로 찾기
        for adrg_name, target_los in self.adrg_to_hira.items():
            if diagnosis in adrg_name or adrg_name in diagnosis:
                return target_los

        return None

    def match_smc_to_hira(
        self,
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        SMC 데이터와 HIRA 데이터 매칭 (ADRG 코드 + 진단명 하이브리드)

        Args:
            smc_df: SMC 데이터프레임 (컬럼: diagnosis, adrg_code 선택)
            hira_df: HIRA 데이터프레임 (컬럼: adrg_name, target_los)

        Returns:
            (매칭된 SMC 데이터프레임, 진단명별 목표 LOS 딕셔너리)
        """
        # HIRA 데이터 로드 (ADRG 코드 + ADRG명)
        self.load_hira_adrg_los(hira_df)

        # 고유 진단명 추출
        unique_diagnoses = smc_df['diagnosis'].unique().tolist()
        unique_adrg_names = hira_df['adrg_name'].unique().tolist()

        # 자동 매칭 생성 (수동 매핑이 없는 경우에만)
        if len(self.diagnosis_to_adrg) == 0:
            auto_mapping = self.create_diagnosis_mapping(
                unique_diagnoses,
                unique_adrg_names
            )
            self.diagnosis_to_adrg.update(auto_mapping)

        # ADRG 코드 있는지 확인
        has_adrg_code = 'adrg_code' in smc_df.columns

        # 진단명별 목표 LOS 딕셔너리 생성
        diagnosis_target_map = {}
        matched_count = 0
        matched_by_code = 0
        matched_by_diagnosis = 0
        total_patients = len(smc_df)

        for diagnosis in unique_diagnoses:
            # 해당 진단의 환자 데이터 가져오기
            diagnosis_df = smc_df[smc_df['diagnosis'] == diagnosis]
            patient_count = len(diagnosis_df)

            # ADRG 코드 우선 시도
            target_los = None
            if has_adrg_code:
                # 가장 많이 나타나는 ADRG 코드 사용
                adrg_codes = diagnosis_df['adrg_code'].value_counts()
                if len(adrg_codes) > 0:
                    most_common_adrg = adrg_codes.index[0]
                    target_los = self.get_target_los(
                        diagnosis,
                        adrg_code=most_common_adrg
                    )
                    if target_los is not None and most_common_adrg != '미매핑':
                        matched_by_code += patient_count

            # ADRG 코드로 매칭 안 되면 진단명으로 시도
            if target_los is None:
                target_los = self.get_target_los(diagnosis)
                if target_los is not None:
                    matched_by_diagnosis += patient_count

            if target_los is not None:
                diagnosis_target_map[diagnosis] = target_los
                matched_count += patient_count

        match_rate = (matched_count / total_patients * 100) if total_patients > 0 else 0
        code_rate = (matched_by_code / total_patients * 100) if total_patients > 0 else 0
        diag_rate = (matched_by_diagnosis / total_patients * 100) if total_patients > 0 else 0

        logger.info(
            f"하이브리드 매칭 완료:\n"
            f"  - 진단명 매칭: {len(diagnosis_target_map)}/{len(unique_diagnoses)}개 "
            f"({len(diagnosis_target_map)/len(unique_diagnoses)*100:.1f}%)\n"
            f"  - 환자 매칭률: {match_rate:.1f}% ({matched_count:,}/{total_patients:,}명)\n"
            f"    * ADRG 코드: {code_rate:.1f}% ({matched_by_code:,}명)\n"
            f"    * 진단명: {diag_rate:.1f}% ({matched_by_diagnosis:,}명)"
        )

        return smc_df, diagnosis_target_map

    def generate_mapping_template(
        self,
        smc_df: pd.DataFrame,
        hira_df: pd.DataFrame,
        output_file: Path | str,
        top_n: int = 100
    ) -> None:
        """
        수동 매핑용 템플릿 엑셀 파일 생성

        Args:
            smc_df: SMC 데이터프레임
            hira_df: HIRA 데이터프레임
            output_file: 출력 파일 경로
            top_n: 상위 N개 진단명만 포함
        """
        # 진단명별 환자 수 집계
        diagnosis_counts = smc_df['diagnosis'].value_counts().head(top_n)

        # HIRA ADRG명 목록
        adrg_names = sorted(hira_df['adrg_name'].unique().tolist())

        # 템플릿 DataFrame 생성
        template_data = []
        for diagnosis, patient_count in diagnosis_counts.items():
            # 자동 매칭 시도
            suggested_adrg = ""
            for adrg_name in adrg_names:
                if diagnosis in adrg_name or adrg_name in diagnosis:
                    suggested_adrg = adrg_name
                    break

            template_data.append({
                'diagnosis': diagnosis,
                'patient_count': patient_count,
                'suggested_adrg': suggested_adrg,
                'adrg_name': suggested_adrg,  # 사용자가 수정할 컬럼
                'note': ''
            })

        df_template = pd.DataFrame(template_data)

        # 엑셀 파일로 저장
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_template.to_excel(writer, sheet_name='매핑', index=False)

            # ADRG 참고 목록 시트 추가
            pd.DataFrame({'adrg_name': adrg_names}).to_excel(
                writer, sheet_name='ADRG목록', index=False
            )

        logger.info(f"매핑 템플릿 생성 완료: {output_path}")
        logger.info(f"  - 상위 {len(template_data)}개 진단명 포함")
        logger.info(f"  - 전체 환자 커버리지: {diagnosis_counts.sum()}/{len(smc_df)}명 "
                   f"({diagnosis_counts.sum()/len(smc_df)*100:.1f}%)")
