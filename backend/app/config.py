"""
애플리케이션 설정 관리
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 애플리케이션 정보
    APP_NAME: str = "병상가동 KPI 산출 프로그램"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./database/bed_kpi.db"

    # 파일 업로드 설정
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: Path = Path("./uploads")

    # 데이터 처리 설정
    MIN_PATIENT_COUNT: int = 6  # 최소 환자수 기준

    # 기간 분류
    OFF_SEASON_MONTHS: list[int] = [3, 4, 11, 12]  # 비수기

    # DRG 매칭 설정
    DRG_MAPPING_FILE: Path = Path("./data/mapping/diagnosis_drg_mapping.xlsx")
    FUZZY_MATCH_THRESHOLD: int = 80  # 퍼지 매칭 최소 신뢰도 (%)

    # 병원 설정
    HOSPITAL_CONFIG: dict = {
        "대전": {"bed_count": 300, "name": "대전선병원"},
        "유성": {"bed_count": 250, "name": "유성선병원"}
    }

    # CORS 설정
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


# 싱글톤 인스턴스
settings = Settings()
