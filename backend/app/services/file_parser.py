"""
파일 파싱 서비스

HIRA 심평원 데이터와 SMC 내부 실적 데이터를 파싱합니다.
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Tuple, Union
import logging

from app.utils.constants import RequiredColumns, ErrorMessages

logger = logging.getLogger(__name__)


class FileParser:
    """파일 파싱 클래스"""

    @staticmethod
    def parse_hira_file(file_path: Path | str) -> pd.DataFrame:
        """
        HIRA 심평원 기준 데이터 파싱

        데이터 특이사항:
        - 헤더가 3번째 행 (skiprows=2, header=0)
        - 첫 데이터 행은 '$' (전체 평균): 제거 필요
        - 실제 유효 데이터: ~740건

        Args:
            file_path: 파일 경로

        Returns:
            파싱된 DataFrame

        Raises:
            FileNotFoundError: 파일을 찾을 수 없음
            ValueError: 필수 컬럼 누락 또는 빈 파일
        """
        try:
            # 파일 존재 확인
            if not Path(file_path).exists():
                raise FileNotFoundError(ErrorMessages.FILE_NOT_FOUND)

            # 엑셀 파일 읽기 (헤더가 3번째 행)
            df = pd.read_excel(
                file_path,
                skiprows=2,  # 처음 2행 스킵
                header=0,     # 3번째 행이 헤더
                engine='openpyxl'
            )

            logger.info(f"HIRA 파일 읽기 완료: {len(df)}건")

            # 필수 컬럼 확인
            required_cols = list(RequiredColumns.HIRA.keys())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    ErrorMessages.MISSING_REQUIRED_COLUMNS.format(
                        columns=", ".join(missing_cols)
                    )
                )

            # 데이터 정제
            # 1. '$' 행 제거 (전체 평균 행)
            df = df[df['4단DRG번호'] != '$']

            # 2. DRG 번호가 없는 행 제거
            df = df[df['4단DRG번호'].notna()]

            # 3. 마지막 타임스탬프 행 제거 (문자열이 너무 길거나 숫자가 아닌 경우)
            df = df[df['평균재원일수'].apply(lambda x: isinstance(x, (int, float)))]

            logger.info(f"HIRA 데이터 정제 완료: {len(df)}건")

            # 빈 데이터 확인
            if df.empty:
                raise ValueError(ErrorMessages.EMPTY_FILE)

            # 컬럼명 변경
            df = df.rename(columns=RequiredColumns.HIRA)

            # 데이터 타입 변환
            df['target_los'] = pd.to_numeric(df['target_los'], errors='coerce')
            df['drg_code'] = df['drg_code'].astype(str).str.strip()
            df['adrg_name'] = df['adrg_name'].astype(str).str.strip()

            # NaN 값이 있는 행 제거
            df = df.dropna(subset=['target_los'])

            # DRG 코드 3자리 추출 (매칭용)
            df['drg_code_3digit'] = df['drg_code'].str[:3]

            logger.info(f"HIRA 데이터 파싱 완료: 최종 {len(df)}건")

            return df

        except Exception as e:
            logger.error(f"HIRA 파일 파싱 오류: {e}")
            raise

    @staticmethod
    def parse_smc_file(
        file_path: Path | str,
        filter_quarter: int | None = None
    ) -> pd.DataFrame:
        """
        SMC 내부 실적 데이터 파싱

        데이터 특이사항:
        - Sheet1에 33,853건의 개별 환자 레벨 데이터
        - 의료진명에 공백 포함 가능 (예: "홍길동 교수") → 공백 전 이름만 추출
        - 컬럼: 구분, 퇴원일자, 성별, 입원일자, 평균재원(=재원일수), 퇴원과, 진단명, 의사명

        Args:
            file_path: 파일 경로
            filter_quarter: 분기 필터 (1=1-3월, 2=4-6월, 3=7-9월, 4=10-12월)
                           None이면 전체 기간

        Returns:
            파싱된 DataFrame

        Raises:
            FileNotFoundError: 파일을 찾을 수 없음
            ValueError: 필수 컬럼 누락 또는 빈 파일
        """
        try:
            # 파일 존재 확인
            if not Path(file_path).exists():
                raise FileNotFoundError(ErrorMessages.FILE_NOT_FOUND)

            # 엑셀 파일 읽기 (Sheet1)
            df = pd.read_excel(
                file_path,
                sheet_name='Sheet1',
                engine='openpyxl'
            )

            logger.info(f"SMC 파일 읽기 완료: {len(df)}건")

            # 필수 컬럼 확인
            required_cols = list(RequiredColumns.SMC.keys())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    ErrorMessages.MISSING_REQUIRED_COLUMNS.format(
                        columns=", ".join(missing_cols)
                    )
                )

            # 빈 데이터 확인
            if df.empty:
                raise ValueError(ErrorMessages.EMPTY_FILE)

            # 데이터 정제
            # 1. 의료진명에서 공백 전 이름만 추출
            df['의사명'] = df['의사명'].astype(str).str.split().str[0]

            # 2. 날짜 형식 변환
            df['퇴원일자'] = pd.to_datetime(df['퇴원일자'], errors='coerce')
            df['입원일자'] = pd.to_datetime(df['입원일자'], errors='coerce')

            # 3. 재원일수 숫자 변환
            df['평균재원'] = pd.to_numeric(df['평균재원'], errors='coerce')

            # 4. 문자열 정제
            df['구분'] = df['구분'].astype(str).str.strip()
            df['퇴원과'] = df['퇴원과'].astype(str).str.strip()
            df['진단명'] = df['진단명'].astype(str).str.strip()

            # 5. NaN 값이 있는 행 제거
            df = df.dropna(subset=['퇴원일자', '평균재원', '진단명', '의사명'])

            logger.info(f"SMC 데이터 정제 완료: {len(df)}건")

            # 컬럼명 변경
            df = df.rename(columns=RequiredColumns.SMC)

            # 기준월 추출 (YYYY-MM 형식)
            df['month'] = df['discharge_date'].dt.to_period('M').astype(str)

            # 분기 필터링 (옵션)
            if filter_quarter is not None:
                if filter_quarter not in [1, 2, 3, 4]:
                    raise ValueError(f"Invalid quarter: {filter_quarter}. Must be 1-4.")

                # 분기별 월 매핑
                quarter_months = {
                    1: [1, 2, 3],
                    2: [4, 5, 6],
                    3: [7, 8, 9],
                    4: [10, 11, 12]
                }

                target_months = quarter_months[filter_quarter]
                df_before = len(df)
                df = df[df['discharge_date'].dt.month.isin(target_months)]

                logger.info(
                    f"SMC 데이터 {filter_quarter}분기 필터링: "
                    f"{df_before}건 → {len(df)}건 "
                    f"({target_months}월)"
                )

            logger.info(f"SMC 데이터 파싱 완료: 최종 {len(df)}건")

            return df

        except Exception as e:
            logger.error(f"SMC 파일 파싱 오류: {e}")
            raise

    @staticmethod
    def validate_files(
        hira_df: pd.DataFrame,
        smc_df: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        파일 유효성 검증

        Args:
            hira_df: HIRA 데이터프레임
            smc_df: SMC 데이터프레임

        Returns:
            (유효성 여부, 에러 메시지)
        """
        try:
            # HIRA 데이터 검증
            if hira_df.empty:
                return False, "HIRA 파일에 데이터가 없습니다"

            if len(hira_df) < 100:
                return False, f"HIRA 데이터가 너무 적습니다 ({len(hira_df)}건). 최소 100건 이상 필요합니다."

            # SMC 데이터 검증
            if smc_df.empty:
                return False, "SMC 파일에 데이터가 없습니다"

            if len(smc_df) < 100:
                return False, f"SMC 데이터가 너무 적습니다 ({len(smc_df)}건). 최소 100건 이상 필요합니다."

            # 병원 구분 확인
            hospitals = smc_df['hospital'].unique()
            valid_hospitals = ['대전', '유성']
            invalid_hospitals = [h for h in hospitals if h not in valid_hospitals]
            if invalid_hospitals:
                return False, f"올바르지 않은 병원명: {', '.join(invalid_hospitals)}"

            # 재원일수 범위 확인 (0.5일 ~ 100일)
            invalid_los = smc_df[
                (smc_df['los_days'] < 0.5) | (smc_df['los_days'] > 100)
            ]
            if len(invalid_los) > len(smc_df) * 0.1:  # 10% 이상 이상치
                return False, f"재원일수 이상치가 너무 많습니다 ({len(invalid_los)}건)"

            # HIRA 목표 LOS 범위 확인
            invalid_hira_los = hira_df[
                (hira_df['target_los'] < 1) | (hira_df['target_los'] > 100)
            ]
            if len(invalid_hira_los) > 0:
                logger.warning(f"HIRA 목표 LOS 이상치: {len(invalid_hira_los)}건")

            return True, "검증 성공"

        except Exception as e:
            logger.error(f"파일 검증 오류: {e}")
            return False, str(e)
