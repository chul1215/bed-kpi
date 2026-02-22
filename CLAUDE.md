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

### Key Services

**file_parser.py** - 파일 파싱:
- `parse_hira_file()`: HIRA 데이터 파싱 (skiprows=2, 739건)
- `parse_smc_file(filter_quarter=None)`: SMC 데이터 파싱 + 분기 필터링 (Sheet1, 33,853건)
- `validate_files()`: 데이터 유효성 검증

**drg_matcher.py** - 진단명 기반 DRG 매칭:
- `load_manual_mapping(file)`: 수동 매핑 테이블 로드
- `match_smc_to_hira()`: SMC 진단명과 HIRA ADRG명 매칭
- `get_target_los(diagnosis)`: 진단명으로 목표 LOS 조회 (수동 → 직접 → 부분 일치)
- `generate_mapping_template()`: 상위 N개 진단명 매핑 템플릿 생성

**kpi_pipeline.py** - 통합 파이프라인:
- `run_pipeline(hira, smc, hospital, filter_quarter)`: 전체 KPI 계산 파이프라인
- 진단명 매칭 → 기간 분류 → 집계 → KPI 산출
- NaN 제거된 disease_target_map 생성 (의료진 KPI 계산용)

**kpi_calculator.py** - KPI 산출 (양방향 유지):
- `calculate_disease_kpi()`: 질환별 KPI (LOS 갭 = target_los - current_los)
- `calculate_doctor_kpi()`: 의료진별 KPI (가중 평균 목표 LOS, None 반환 시 status='no_target_los')
- `calculate_summary_kpi()`: 요약 KPI (평균 갭, 추가 재원일수, 가동률)

**aggregator.py** - 데이터 집계:
- `aggregate_by_disease()`: 질환 단위 집계
- `aggregate_by_doctor()`: 의료진 단위 집계
- `aggregate_by_department()`: 진료과 단위 집계
- `aggregate_by_doctor_disease()`: 의료진-질환 교차 집계 (의료진 KPI 계산용)

**period_classifier.py** - 기간 분류:
- 비수기: 3-4월, 11-12월
- 통상기간: 1-2월, 5-10월

**dashboard_generator.py** - HTML 대시보드 생성:
- `render_home()`: 홈 화면 (KPI 카드 + TOP 6 랭킹 + 검색)
- `render_department()`: 진료과 뷰
- `render_doctor()`: 의료진 상세
- `render_disease()`: 질환 상세
- NaN → None → "N/A" 처리 로직 포함

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

**DRG 매칭 전략 (진단명 기반):**
- **현재 상태**: 46개 진단명 매칭 (수동 15개 + 자동 31개)
- **방법**: HIRA ADRG명과 SMC 진단명을 직접 매칭 (ICD-10 코드 불필요)
- **매핑 파일**: `data/mapping/diagnosis_drg_mapping.xlsx` (수동 매핑 테이블)
- **템플릿**: `data/mapping/diagnosis_drg_mapping_template.xlsx` (상위 100개 진단명 + 제안 ADRG)
- **결과**: 대전 비수기 기준 32명/42명 의료진에 데이터 표시 (76%)
- **주요 매핑 예시**:
  - 협심증 → 협심증
  - 급성 충수염 → 복잡한 주진단이 없는 충수절제술
  - 담석증 → 복강경을 이용한 전담낭절제술
  - 상세불명 병원체의 폐렴 → 세균성 폐렴
- **매칭률 향상**: 템플릿 파일에서 상위 진단명을 확인하여 `diagnosis_drg_mapping.xlsx`에 추가

### Data Filtering Rules

```python
MIN_PATIENT_COUNT = 6  # 환자수 6명 미만 제외
LOS_RANGE = (0.5, 100)  # 재원일수 정상 범위
```

---

## Development Phases

현재: **정적 HTML 대시보드 생성 완료** ✅ (GitHub Pages 배포 준비 완료)

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

### ✅ Day 3 완료: 파일 업로드 & 동적 데이터 연동
- [x] kpi_pipeline.py (Day 1 서비스 통합 ✅)
- [x] memory_store.py (세션 관리 및 데이터 저장소 ✅)
- [x] upload.py (파일 업로드 API - POST /api/upload/files ✅)
- [x] upload.html (업로드 UI 페이지 ✅)
- [x] 동적 데이터 로딩 (session_id 기반 실제 KPI 표시 ✅)
- [x] E2E 테스트 통과 (5/5 PASS ✅)

### ✅ 정적 HTML 대시보드 생성 완료 (진단명 기반 매칭)
- [x] generate_static_dashboard.py (서버 없이 파일 시스템에서 직접 실행 가능)
- [x] **파일 경로 기반 네비게이션** (병원/기간 전환 작동)
  - 병원 전환: `../유성/index_off_season.html`
  - 기간 전환: `index_normal.html`
  - 서브디렉토리: `../../대전/index_off_season.html`
- [x] 대전/유성 병원별 HTML 생성 (각 44개 파일, 총 88개)
- [x] 비수기/통상기간별 페이지 분리
- [x] docs/ 폴더 구조 (GitHub Pages 배포 준비 완료)
- [x] NaN 값 안전 처리 (None → "N/A")
- [x] 진단명 기반 DRG 매칭 적용 (46개 진단명, 32명 의료진 데이터 표시)

### 📊 현재 상태 (2026-02-22)
- **DRG 매칭**: 46개 진단명 매칭 완료 (14.2%)
- **환자 커버리지**: ~30% (추정)
- **의료진 데이터**: 대전 비수기 기준 32명/42명 (76%)
- **정적 HTML**: 88개 파일 생성, 즉시 실행 가능
- **배포 준비**: GitHub Pages 배포 가능 상태

### 향후 개선 사항 (선택적)
- [ ] DRG 매핑 테이블 확장 (현재 46개 → 목표 100개+)
  - 상위 100개 진단명 매핑 시 환자 커버리지 60%+ 예상
  - `diagnosis_drg_mapping_template.xlsx` 참조
- [ ] 병원 시스템에서 ICD-10 코드 포함 데이터 확보
  - DRG 청구 데이터는 ICD-10 코드 포함되어 있어야 함
- [ ] HIRA 연간 데이터 확보 (현재: 4분기만)
- [ ] 데이터베이스 연동 (SQLite/PostgreSQL)
- [ ] 엑셀 다운로드 기능
- [ ] DRG 매핑 관리 UI
- [ ] 사용자 인증
- [ ] Docker 배포

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

## Static HTML Generation

### Generate Static Dashboard (서버 없이 직접 실행 가능)

```bash
# 정적 HTML 생성 (진단명 기반 DRG 매칭 적용)
python3 generate_static_dashboard.py
```

**출력**: `docs/` 폴더에 88개 HTML 파일 생성
- 대전/유성 병원별 × 비수기/통상기간별
- 홈, 진료과, 의료진 상세(10명), 질환 상세(10개)

**중요 특징**:
- 파일 경로 기반 네비게이션 (URL 파라미터 없이 작동)
- NaN 값 안전 처리 (None → "N/A")
- 진단명 기반 DRG 매칭 (46개 진단명)
- 진료과/의료진 검색 기능

### 로컬에서 확인

```bash
# 방법 1: 파일 직접 더블클릭 (권장)
open docs/index.html

# 방법 2: 간단한 웹서버 (선택)
cd docs && python3 -m http.server 8080
# http://localhost:8080 접속
```

### 매칭률 향상 방법

현재 46개 진단명 매칭 → 더 많은 진단명 추가:

```bash
# 1. 템플릿 확인 (상위 100개 진단명 + 제안 ADRG)
open data/mapping/diagnosis_drg_mapping_template.xlsx

# 2. 수동 매핑 추가
# data/mapping/diagnosis_drg_mapping.xlsx 편집
# - diagnosis: SMC 진단명
# - adrg_name: HIRA ADRG명 (템플릿의 "ADRG목록" 시트 참조)

# 3. 재생성
python3 generate_static_dashboard.py
```

### GitHub Pages 배포

```bash
# 1. 커밋 및 푸시
git add docs/ data/mapping/
git commit -m "Update dashboard with diagnosis-based DRG matching"
git push origin main

# 2. GitHub Settings > Pages
# Source: main branch, /docs folder

# 3. 배포 URL
# https://<username>.github.io/<repository>/
```

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

### Testing DRG Matching

```python
from app.services.drg_matcher import DRGMatcher
from app.services.file_parser import FileParser
from app.config import settings, PROJECT_ROOT

# 파일 로드
hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
smc_df = FileParser.parse_smc_file(settings.PRELOADED_SMC_FILE, filter_quarter=4)
smc_df = smc_df[smc_df['hospital'] == '대전']

# DRG Matcher 초기화 및 매핑 로드
matcher = DRGMatcher()
mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_drg_mapping.xlsx'
matcher.load_manual_mapping(mapping_file)

# 매칭 실행
smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_df, hira_df)

print(f"매칭된 진단명: {len(disease_target_map)}개")
print(f"환자 커버리지: {sum(1 for d in smc_df['diagnosis'] if d in disease_target_map)}/{len(smc_df)}명")
```

### Generating Mapping Template

```python
from app.services.drg_matcher import DRGMatcher
from pathlib import Path

matcher = DRGMatcher()
matcher.generate_mapping_template(
    smc_df,
    hira_df,
    Path('../data/mapping/diagnosis_drg_mapping_template.xlsx'),
    top_n=100  # 상위 100개 진단명
)
```

---

## Key Implementation Learnings

### 진단명 기반 DRG 매칭 (Diagnosis-Based Matching)

**배경**: SMC 데이터에 ICD-10 코드가 존재하지 않아 코드 기반 매칭 불가능

**해결책**:
1. HIRA ADRG명과 SMC 진단명을 직접 매칭
2. 3단계 매칭 전략:
   - 수동 매핑 테이블 우선 (diagnosis_drg_mapping.xlsx)
   - 직접 일치 (진단명 = ADRG명)
   - 부분 일치 (진단명 in ADRG명 or ADRG명 in 진단명)

**핵심 코드**:
```python
# drg_matcher.py
def get_target_los(self, diagnosis: str) -> float | None:
    diagnosis = str(diagnosis).strip()

    # 1. 수동 매핑 테이블
    if diagnosis in self.diagnosis_to_adrg:
        adrg_name = self.diagnosis_to_adrg[diagnosis]
        if adrg_name in self.adrg_to_hira:
            return self.adrg_to_hira[adrg_name]

    # 2. 직접 일치
    if diagnosis in self.adrg_to_hira:
        return self.adrg_to_hira[diagnosis]

    # 3. 부분 일치
    for adrg_name, target_los in self.adrg_to_hira.items():
        if diagnosis in adrg_name or adrg_name in diagnosis:
            return target_los

    return None
```

### 정적 HTML 네비게이션 (Static HTML Navigation)

**문제**: URL 파라미터 방식은 정적 파일(file://)에서 작동하지 않음

**해결책**: 파일 경로 기반 네비게이션으로 JavaScript 동적 교체

**핵심 개념**:
```javascript
// generate_static_dashboard.py에서 주입
function switchHospital(targetHospital) {
    const currentPeriod = 'off_season';  // 템플릿 변수
    const path = `../${targetHospital}/index_${currentPeriod}.html`;
    window.location.href = path;
}

function switchPeriod(targetPeriod) {
    const path = `index_${targetPeriod}.html`;
    window.location.href = path;
}
```

**디렉토리별 경로 패턴**:
- 루트 레벨 (`대전/index.html`): `../유성/index.html`
- 서브디렉토리 (`대전/doctors/의사.html`): `../../유성/doctors/의사.html`

### NaN 값 처리 (NaN Handling)

**문제**: pandas DataFrame에서 None이 NaN으로 변환되어 JSON/템플릿에서 문제 발생

**해결책**: 3단계 방어

1. **KPI 계산**: 매칭 실패 시 None 반환
```python
if total_matched == 0:
    return {'target_los': None, 'los_gap': None, ...}
```

2. **파이프라인**: NaN 제거한 매핑 딕셔너리
```python
disease_target_map = {
    diagnosis: target_los
    for diagnosis, target_los in zip(...)
    if pd.notna(target_los)  # NaN 제거
}
```

3. **템플릿**: None 값 안전 표시
```jinja2
{{ doctor.los_gap if doctor.los_gap is not none else 'N/A' }}
```

---

## 참고 문서

**완료 보고서**:
- [DIAGNOSIS_MATCHING_COMPLETE.md](DIAGNOSIS_MATCHING_COMPLETE.md) - 진단명 기반 매칭 완료 보고
- [실행방법.md](실행방법.md) - 사용자 실행 가이드

**기획 문서** (plan/ 폴더):
- `병상가동 KPI 산출 프로그램 PRD.md` - 요구사항 정의
- `선메디컬센터 시기별 병상가동 KPI 산출 프로그램 기획안.md` - 기획 의도
- `병상가동 KPI 프로그램 와이어프레임.md` - UI 설계
