"""
기간 분류 서비스

비수기(3-4월, 11-12월)와 통상기간(1-2월, 5-10월)을 분류합니다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Union
import pandas as pd
import logging

from app.config import settings
from app.utils.constants import Period

logger = logging.getLogger(__name__)


class PeriodClassifier:
    """기간 분류 클래스"""

    @staticmethod
    def classify_period(date: datetime | pd.Timestamp) -> str:
        """
        날짜를 기준으로 기간 분류

        Args:
            date: 날짜 (datetime 또는 pandas Timestamp)

        Returns:
            기간 구분 ('off_season' 또는 'normal')
        """
        month = date.month

        if month in settings.OFF_SEASON_MONTHS:
            return Period.OFF_SEASON
        else:
            return Period.NORMAL

    @staticmethod
    def add_period_column(df: pd.DataFrame, date_column: str = 'discharge_date') -> pd.DataFrame:
        """
        DataFrame에 기간 구분 컬럼 추가

        Args:
            df: 데이터프레임
            date_column: 날짜 컬럼명 (기본값: 'discharge_date')

        Returns:
            기간 구분 컬럼이 추가된 DataFrame
        """
        if date_column not in df.columns:
            raise ValueError(f"'{date_column}' 컬럼이 존재하지 않습니다")

        # 복사본 생성
        result_df = df.copy()

        # pandas Series에 vectorized 연산 적용
        result_df['period'] = result_df[date_column].apply(lambda d: PeriodClassifier.classify_period(d))

        logger.info(
            f"기간 분류 완료 - "
            f"비수기: {len(result_df[result_df['period'] == Period.OFF_SEASON])}건, "
            f"통상기간: {len(result_df[result_df['period'] == Period.NORMAL])}건"
        )

        return result_df

    @staticmethod
    def get_period_stats(df: pd.DataFrame) -> dict:
        """
        기간별 통계 조회

        Args:
            df: 기간 구분 컬럼이 있는 DataFrame

        Returns:
            기간별 통계 딕셔너리
        """
        if 'period' not in df.columns:
            raise ValueError("'period' 컬럼이 존재하지 않습니다")

        stats = {
            Period.OFF_SEASON: {
                "count": len(df[df['period'] == Period.OFF_SEASON]),
                "months": settings.OFF_SEASON_MONTHS
            },
            Period.NORMAL: {
                "count": len(df[df['period'] == Period.NORMAL]),
                "months": [m for m in range(1, 13) if m not in settings.OFF_SEASON_MONTHS]
            }
        }

        return stats

    @staticmethod
    def calculate_period_days(year: int = 2025) -> dict:
        """
        기간별 일수 계산

        Args:
            year: 연도 (기본값: 2025)

        Returns:
            기간별 일수 딕셔너리
        """
        # 각 월의 일수
        month_days = {
            1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }

        # 윤년 확인
        is_leap_year = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        if is_leap_year:
            month_days[2] = 29

        # 비수기 일수 계산
        off_season_days = sum(month_days[m] for m in settings.OFF_SEASON_MONTHS)

        # 통상기간 일수 계산
        normal_days = sum(
            days for month, days in month_days.items()
            if month not in settings.OFF_SEASON_MONTHS
        )

        return {
            Period.OFF_SEASON: off_season_days,
            Period.NORMAL: normal_days,
            "total": 366 if is_leap_year else 365
        }

    @staticmethod
    def filter_by_period(
        df: pd.DataFrame,
        period: str,
        period_column: str = 'period'
    ) -> pd.DataFrame:
        """
        특정 기간으로 필터링

        Args:
            df: 데이터프레임
            period: 기간 구분 ('off_season' 또는 'normal')
            period_column: 기간 컬럼명 (기본값: 'period')

        Returns:
            필터링된 DataFrame
        """
        if period_column not in df.columns:
            raise ValueError(f"'{period_column}' 컬럼이 존재하지 않습니다")

        if period not in [Period.OFF_SEASON, Period.NORMAL]:
            raise ValueError(
                f"올바르지 않은 기간 구분: {period}. "
                f"'{Period.OFF_SEASON}' 또는 '{Period.NORMAL}'을 사용하세요."
            )

        filtered_df = df[df[period_column] == period].copy()

        logger.info(f"{period} 필터링 완료: {len(filtered_df)}건")

        return filtered_df

    # Alias for compatibility
    @staticmethod
    def classify_dataframe(df: pd.DataFrame, date_column: str = 'discharge_date') -> pd.DataFrame:
        """
        DataFrame에 기간 구분 컬럼 추가 (add_period_column의 alias)

        Args:
            df: 데이터프레임
            date_column: 날짜 컬럼명 (기본값: 'discharge_date')

        Returns:
            기간 구분 컬럼이 추가된 DataFrame
        """
        return PeriodClassifier.add_period_column(df, date_column)
