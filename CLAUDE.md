# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**병상가동 KPI 산출 프로그램** - 선메디컬센터(대전선병원/유성선병원) 시기별 병상가동 KPI 산출 웹 대시보드

**Purpose:**
- 심평원 기준 재원일수 대비 자체 재원일수 격차를 정량화
- 비수기(3-4월, 11-12월) / 통상기간(1-2월, 5-10월) 분리 관리
- 진료과-의료진-질환 단위 목표 관리 체계 구축

**Tech Stack:**
- Backend: Python 3.9+ with FastAPI + pandas + Jinja2 + Plotly
- Frontend: HTML5 + Bootstrap 5 (와이어프레임 기반)
- Data Processing: pandas, openpyxl for Excel parsing
- Database: SQLite (추후)

---

## Running the Application

### Backend (FastAPI)

```bash
# 의존성 설치
cd backend
pip3 install -r requirements.txt

# 개발 서버 실행
python3 -m app.main

# 또는
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버 실행 후: http://localhost:8000

### Testing

```bash
# Day 1 완전한 파이프라인 테스트 (권장)
cd backend
python3 tests/test_kpi_engine.py

# 특정 서비스 수동 테스트
python3 -c "
from app.services.file_parser import FileParser
hira_df = FileParser.parse_hira_file('../data/hira/*.xlsx')
print(f'HIRA: {len(hira_df)}건')
"
```

---

## Architecture

### Data Pipeline Flow

```
파일 업로드 → 파싱 → 검증 → 기간 분류 → DRG 매칭 →
집계 → KPI 산출 → DB 저장 → API 응답
```

### Backend Structure

```
backend/app/
├── main.py                      # FastAPI 앱 진입점 + 정적 파일 서빙
├── config.py                    # 설정 (MIN_PATIENT_COUNT=6, OFF_SEASON_MONTHS 등)
├── models/                      # Pydantic 모델
├── services/                    # 비즈니스 로직 (Day 1 완성)
│   ├── file_parser.py          # HIRA/SMC 파일 파싱 ✅
│   ├── period_classifier.py     # 비수기/통상기간 분류 ✅
│   ├── aggregator.py           # 질환/의료진/진료과 집계 ✅
│   ├── kpi_calculator.py       # KPI 산출 엔진 ✅
│   ├── drg_matcher.py          # DRG 매칭 ✅
│   └── dashboard_generator.py  # HTML 대시보드 생성 (Day 2 진행중)
├── api/                         # API 라우터 (Day 2 진행중)
│   └── dashboard.py            # 대시보드 API 엔드포인트
├── templates/                   # Jinja2 HTML 템플릿 (Day 2 진행중)
│   ├── base.html               # 공통 헤더/레이아웃
│   ├── index.html              # 홈 (KPI 카드 + 의사별 TOP 6)
│   ├── department.html         # 진료과 뷰
│   ├── doctor.html             # 의료진 상세
│   └── disease.html            # 질환 뷰
├── static/                      # CSS/JS (Day 2 진행중)
│   ├── style.css               # Bootstrap + 커스텀 스타일
│   └── charts.js               # Plotly 차트 스크립트
└── utils/
    └── constants.py            # 상수 (Period, UploadStatus 등)
```

### Key Services (Day 1 완성)

**file_parser.py** - 파일 파싱:
- `parse_hira_file()`: HIRA 데이터 파싱 (skiprows=2, 739건 ✅)
- `parse_smc_file()`: SMC 데이터 파싱 (Sheet1, 33,853건 ✅)
- `validate_files()`: 데이터 유효성 검증 ✅

**aggregator.py** - 데이터 집계:
- `aggregate_by_disease()`: 질환 단위 집계
- `aggregate_by_doctor()`: 의료진 단위 집계
- `aggregate_by_department()`: 진료과 단위 집계
- `calculate_consistency_error()`: 정합성 검증 (진료과 합계 = 의료진 합계)

**kpi_calculator.py** - KPI 산출 (양방향 유지):
- `calculate_disease_kpi()`: 질환별 KPI (LOS 갭 = target_los - current_los)
- `calculate_doctor_kpi()`: 의료진별 KPI (가중 평균 목표 LOS)
- `calculate_summary_kpi()`: 요약 KPI (평균 갭, 추가 병상일수, 가동률)

**period_classifier.py** - 기간 분류:
- 비수기: 3-4월, 11-12월 (비수기 데이터: 11,330건)
- 통상기간: 1-2월, 5-10월 (통상기간 데이터: 22,523건)

---

## Domain Concepts

### Key Terms and Definitions

- **선메디컬센터** = 대전선병원 + 유성선병원 (two hospitals under one medical center)
- **LOS (Length of Stay)**: 재원일수 = 병상일수 / 환자수
- **LOS 갭**: HIRA_목표_LOS - 현재_LOS (**양방향 유지**: 양수면 늘려야 함, 음수면 줄여야 함)
- **추가 병상일수**: LOS_갭 × 환자수 (임팩트 점수, **부호 유지**)
- **비수기**: 3-4월, 11-12월 (환자 감소 기간)
- **통상기간**: 1-2월, 5-10월

### Key Formulas (KPI 산출)

```python
# 질환/의료진 공통
current_los = total_bed_days / patient_count
los_gap = target_los - current_los  # 양수: 늘려야 함, 음수: 줄여야 함
additional_bed_days = los_gap * patient_count

# 의료진 목표 LOS (가중 평균)
doctor_target_los = Σ(disease_target_los × disease_patient_count) / total_patient_count
```

### Data Specifications

**HIRA 파일 특이사항:**
- 헤더가 3번째 행 (`skiprows=2`)
- 첫 데이터 행은 '$' (전체 평균) → 제거 필요
- 컬럼: 4단DRG번호, ADRG명, 평균재원일수
- DRG 코드 3자리 추출하여 매칭에 사용

**SMC 파일 특이사항:**
- Sheet1에 개별 환자 레벨 데이터
- 의료진명에 공백 포함 가능 (예: "홍길동 교수") → 공백 전 이름만 추출
- 컬럼: 구분(병원), 퇴원일자, 평균재원(=재원일수), 퇴원과, 진단명, 의사명

**DRG 매칭 전략:**
- SMC는 진단명(한글)만, HIRA는 DRG 코드 + ADRG명 제공 → 직접 매칭 불가
- `data/mapping/diagnosis_drg_mapping.xlsx` 수동 매핑 테이블 필요
- 퍼지 매칭 (fuzzywuzzy) 신뢰도 80% 이상 자동 매칭

### Data Filtering Rules

```python
MIN_PATIENT_COUNT = 6  # 환자수 6명 미만 제외
LOS_RANGE = (0.5, 100)  # 재원일수 정상 범위
```

---

## Development Phases

현재: **Day 2 (HTML 대시보드)** ✅ 완료, **Day 3 (최종 검증)** 준비 중

### ✅ Day 1 완료: 데이터 파이프라인
- [x] FastAPI 프로젝트 초기화
- [x] file_parser.py (HIRA 739건, SMC 33,853건 ✅)
- [x] period_classifier.py (비수기 11,330건, 통상기간 22,523건 ✅)
- [x] aggregator.py (질환/의료진/진료과 집계 ✅)
- [x] kpi_calculator.py (KPI 산출 엔진 ✅)
- [x] drg_matcher.py (DRG 매칭 ✅)
- [x] 정합성 검증 통과 ✅

### ✅ Day 2 완료: HTML 대시보드 (와이어프레임 기반)
- [x] dashboard_generator.py (Jinja2 템플릿 렌더링 ✅)
- [x] 공통 헤더 (base.html - 병원/기간 토글, 네비게이션 ✅)
- [x] 홈 화면 (index.html - KPI 카드 3종 + 의사별 질환 TOP 6 ✅)
- [x] 진료과 뷰 (department.html - 진료과 랭킹 + 드릴다운 ✅)
- [x] 의료진 상세 (doctor.html - KPI 카드 + 질환별 상세 ✅)
- [x] 질환 뷰 (disease.html - HIRA 기준 + 담당 의료진 분포 ✅)
- [x] FastAPI 라우트 통합 (4개 주요 페이지 + health ✅)

### Phase 2: KPI 산출 엔진 (1-2주)
- kpi_calculator.py (핵심 알고리즘)
- KPI 조회 API
- 정합성 검증 (진료과 합계 = 전체 합계)

### Phase 3-6: 프론트엔드, 테스트, 대시보드, 배포
상세 내용은 `/Users/chul/.claude/plans/magical-soaring-blossom.md` 참조

---

## Critical Implementation Notes

### Python Version Compatibility

**Python 3.9 사용 중** - 타입 힌트 주의:
```python
# ❌ Python 3.10+ only
def parse_file(path: Path | str) -> pd.DataFrame:

# ✅ Python 3.9 compatible
from __future__ import annotations
def parse_file(path: Path | str) -> pd.DataFrame:
```

모든 서비스 파일은 `from __future__ import annotations` 포함 필수

### File Parsing Gotchas

**HIRA 파일:**
- `skiprows=2, header=0` 필수
- 첫 행 '$' 제거: `df = df[df['4단DRG번호'] != '$']`
- 마지막 타임스탬프 행 제거

**SMC 파일:**
- Sheet1만 사용
- 의료진명 정제: `df['의사명'].str.split().str[0]`

### Configuration

모든 설정은 `app/config.py`의 `Settings` 클래스에서 관리:
- `MIN_PATIENT_COUNT = 6`
- `OFF_SEASON_MONTHS = [3, 4, 11, 12]`
- `DRG_MAPPING_FILE = "./data/mapping/diagnosis_drg_mapping.xlsx"`
- `HOSPITAL_CONFIG = {"대전": {"bed_count": 300}, "유성": {"bed_count": 250}}`

### Database Schema

SQLite 사용, 주요 테이블:
- `upload_sessions`: 업로드 세션 관리
- `disease_kpis`: 질환별 KPI
- `doctor_kpis`: 의료진별 KPI
- `drg_mappings`: DRG 매핑 테이블
- `hospital_config`: 병원 설정 (병상 수 등)

---

## Document Consistency Rules

When editing planning documents or implementing features, ensure consistency:

**Core Business Rules:**
- Hospital name: "선메디컬센터" (use individual names only when listing separately: 대전선병원, 유성선병원)
- **LOS 갭 formula**: Always bidirectional - NO `max(0, ...)`. Preserve positive/negative sign.
- 내부 실적 필수 컬럼: 병원명, 기준월, 진료과, 의료진, 질환, 환자수, 병상일수
- 홈 화면 랭킹: 의사별 질환 TOP 6 (환자수 기준) + 의사 KPI

**UI Specifications:**
- 병원 탭: [대전선병원] / [유성선병원]
- 기간 토글: [비수기 (3-4·11-12월)] / [통상기간] / [월별 선택]

---

## Reference Documentation

**Planning Docs** (plan/ 폴더):
- `병상가동 KPI 산출 프로그램 PRD.md`: 상세 요구사항, FR-01 ~ FR-10
- `선메디컬센터 시기별 병상가동 KPI 산출 프로그램 기획안.md`: 기획 의도, KPI 정의
- `병상가동 KPI 프로그램 와이어프레임.md`: UI 화면 설계

**Implementation Plan:**
- `/Users/chul/.claude/plans/magical-soaring-blossom.md`: 전체 구현 계획 (6 Phases)

**Note on plan/ folder:**
- Contains Obsidian vault documents (PRD, 기획안, 와이어프레임)
- Uses `[[wikilink]]` syntax for cross-references
- Critical content from plan/CLAUDE.md is integrated above

**Key Domain Terms:**
- **LOS (Length of Stay)**: 재원일수 = 병상일수 / 환자수
- **LOS 갭**: HIRA_목표_LOS - 현재_LOS (양수면 늘려야 함, 음수면 줄여야 함)
- **추가 병상일수**: LOS_갭 × 환자수 (임팩트 점수)
- **비수기**: 3-4월, 11-12월 (환자 감소 기간)
- **통상기간**: 1-2월, 5-10월

---

## Common Tasks

### Adding a New Service

1. `backend/app/services/` 폴더에 파일 생성
2. `from __future__ import annotations` 추가 (Python 3.9 호환)
3. 클래스 기반으로 작성, `@staticmethod` 활용
4. `tests/` 폴더에 테스트 파일 작성
5. 필요시 `app/models/`에 Pydantic 모델 정의

### Testing Data Pipeline

```python
# HIRA 파싱 테스트
from app.services.file_parser import FileParser
hira_df = FileParser.parse_hira_file('../data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx')
print(f"HIRA: {len(hira_df)}건")  # 예상: ~739건

# SMC 파싱 테스트
smc_df = FileParser.parse_smc_file('../data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx')
print(f"SMC: {len(smc_df)}건")  # 예상: ~33,853건

# 유효성 검증
is_valid, msg = FileParser.validate_files(hira_df, smc_df)
```

### Verifying KPI Calculations

모든 KPI 계산은 정합성 검증 필수:
```python
# 진료과 합계 = 전체 합계
total_patients_disease = disease_kpis['patient_count'].sum()
total_patients_doctor = doctor_kpis['patient_count'].sum()
assert total_patients_disease == total_patients_doctor
```
