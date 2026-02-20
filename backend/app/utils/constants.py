"""
상수 정의
"""

# 기간 구분
class Period:
    OFF_SEASON = "off_season"  # 비수기
    NORMAL = "normal"  # 통상기간


# 업로드 상태
class UploadStatus:
    PENDING = "pending"  # 대기 중
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


# 필수 컬럼 정의
class RequiredColumns:
    """필수 컬럼 정의"""

    # HIRA 파일 필수 컬럼
    HIRA = {
        "4단DRG번호": "drg_code",
        "ADRG명": "adrg_name",
        "평균재원일수": "target_los"
    }

    # SMC 파일 필수 컬럼
    SMC = {
        "구분": "hospital",
        "퇴원일자": "discharge_date",
        "평균재원": "los_days",
        "퇴원과": "department",
        "진단명": "diagnosis",
        "의사명": "doctor"
    }


# 정렬 기준
class SortBy:
    PATIENT_COUNT = "patient_count"  # 환자수
    LOS_GAP = "los_gap"  # LOS 갭
    ADDITIONAL_BED_DAYS = "additional_bed_days"  # 추가 병상일수
    CURRENT_LOS = "current_los"  # 현재 LOS


# 에러 메시지
class ErrorMessages:
    FILE_NOT_FOUND = "파일을 찾을 수 없습니다"
    INVALID_FILE_FORMAT = "올바르지 않은 파일 형식입니다"
    MISSING_REQUIRED_COLUMNS = "필수 컬럼이 누락되었습니다: {columns}"
    EMPTY_FILE = "파일에 데이터가 없습니다"
    INVALID_DATA_RANGE = "데이터 범위가 올바르지 않습니다"
    SESSION_NOT_FOUND = "세션을 찾을 수 없습니다"
    PROCESSING_ERROR = "데이터 처리 중 오류가 발생했습니다"
