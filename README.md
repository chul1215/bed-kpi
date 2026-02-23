# 병상가동 KPI 산출 프로그램

선메디컬센터(대전선병원/유성선병원) 시기별 병상가동 KPI 산출 웹 대시보드

## 📋 프로젝트 개요

### 목적
- 심평원 기준 재원일수 대비 자체 재원일수 격차를 정량화
- 비수기(3-4월, 11-12월) / 통상기간(1-2월, 5-10월) 분리 관리
- 진료과-의료진-질환 단위 목표 관리 체계 구축

### 주요 성과 (2026-02-23)
- ✅ **96.3% 매칭률** 달성 (7,768명 / 8,063명)
- ✅ **전체 160명 의료진 모두 80% 이상** 매칭률 달성
- ✅ 정적 HTML 대시보드 생성 완료 (88개 파일)
- ✅ GitHub Pages 배포 준비 완료

### 기술 스택
- **Backend**: Python 3.9+ (FastAPI, pandas, Jinja2)
- **Frontend**: HTML5 + Bootstrap 5
- **Data Processing**: pandas, openpyxl
- **Matching**: ICD-10 자동 (282개) + 진단명 수동 (164개)

---

## 🚀 빠른 시작

### 정적 대시보드 생성 (권장)

```bash
# 정적 HTML 대시보드 생성
python3 generate_static_dashboard.py

# 로컬에서 확인
open docs/index.html
```

### FastAPI 서버 실행 (개발용)

```bash
# 의존성 설치
cd backend
pip3 install -r requirements.txt

# 서버 실행
python3 -m app.main
# 또는
uvicorn app.main:app --reload --port 8000
```

서버는 `http://localhost:8000`에서 실행됩니다.

---

## 📁 프로젝트 구조

```
bed-kpi/
├── backend/                    # Python FastAPI 백엔드
│   ├── app/
│   │   ├── main.py            # FastAPI 앱 진입점
│   │   ├── config.py          # 설정 (MIN_PATIENT_COUNT=6 등)
│   │   ├── services/          # 비즈니스 로직 ✅
│   │   │   ├── file_parser.py          # HIRA/SMC 파일 파싱
│   │   │   ├── period_classifier.py    # 기간 분류
│   │   │   ├── kdrg_matcher.py         # ICD-10 + 진단명 매칭
│   │   │   ├── aggregator.py           # 데이터 집계
│   │   │   ├── kpi_calculator.py       # KPI 산출
│   │   │   └── kpi_pipeline.py         # 통합 파이프라인
│   │   ├── templates/         # Jinja2 HTML 템플릿
│   │   └── api/               # API 라우터
│   └── requirements.txt
│
├── data/
│   ├── hira/                  # 심평원 기준 데이터 (739건)
│   ├── smc/                   # SMC 내부 실적 데이터 (8,063건)
│   └── mapping/               # DRG 매핑 테이블
│       ├── icd10_to_adrg_from_kdrg46.xlsx    # ICD-10 자동 매핑 (282개)
│       └── diagnosis_kdrg44_mapping.xlsx      # 진단명 수동 매핑 (164개)
│
├── docs/                      # 정적 HTML 대시보드 (88개 파일)
│   ├── index.html             # 메인 페이지 (리디렉션)
│   ├── 대전/                  # 대전선병원 (44개 파일)
│   └── 유성/                  # 유성선병원 (44개 파일)
│
├── plan/                      # 프로젝트 계획 문서
│
├── archive/                   # 개발 히스토리 아카이브
│   ├── reports/               # 중간 보고서
│   ├── scripts/               # 일회성 스크립트
│   └── old_docs/              # 구버전 문서
│
├── generate_static_dashboard.py    # 정적 대시보드 생성 스크립트
├── add_top10_mappings.py           # TOP 10 매핑 추가 (1단계)
├── add_all_icd10_mappings.py       # ICD-10 전체 매핑 (2단계)
│
├── CLAUDE.md                  # 개발 가이드 (개발자용)
├── README.md                  # 프로젝트 개요 (이 파일)
└── 실행방법.md                # 사용자 가이드
```

---

## 📊 핵심 개념

### KPI 산출 공식

```python
# 현재 재원일수
current_los = 총병상일수 / 환자수

# LOS 갭 (양방향 유지)
los_gap = HIRA_목표_LOS - 현재_LOS
# ➕ 양수: 재원일수를 늘려야 함
# ➖ 음수: 재원일수를 줄여야 함 (이미 효율적)

# 추가 재원일수 (임팩트)
additional_bed_days = los_gap × 환자수

# 가동률 갭
utilization_gap = (additional_bed_days / 가용병상일수) × 100
```

### 기간 구분
- **비수기**: 3월, 4월, 11월, 12월 (122일)
- **통상기간**: 1월, 2월, 5월~10월 (243일)

### DRG 매칭 전략
1. **ICD-10 코드 기반 자동 매칭** (우선순위 높음)
   - KDRG 4.6 전체 코드 (282개)
2. **진단명 수동 매핑** (164개)
3. **진단명 직접/부분 일치**

### 데이터 필터링
- **질환별 KPI 표시**: 환자수 6명 이상만 (통계적 유의성)
- **의료진 KPI 계산**: 모든 환자 포함 (실제 성과 반영)

---

## 📊 현재 상태

### 매칭 성과
- **전체 매칭률**: 96.3% (7,768명 / 8,063명)
- **ICD-10 자동**: 282개 코드
- **진단명 수동**: 164개
- **의료진 매칭**: 160명 전원 80% 이상 ✅

### 생성 파일
- **정적 HTML**: 88개 파일
  - 대전/유성 × 비수기/통상 = 4개 조합
  - 각 조합: 홈(1) + 진료과(1) + 의사(10) + 질환(10) = 22개
- **배포**: GitHub Pages 준비 완료

---

## 🧪 테스트

### 데이터 파이프라인 테스트

```bash
cd backend
python3 tests/test_kpi_engine.py
```

### 매칭률 확인

```python
from app.services.kpi_pipeline import KPIPipeline
from app.config import settings

pipeline = KPIPipeline()
result = pipeline.run_pipeline(
    hira_file_path=settings.PRELOADED_HIRA_FILE,
    smc_file_path=settings.PRELOADED_SMC_FILE,
    hospital='대전',
    filter_quarter=4
)

print(f"매칭률: {result['summary_kpi_off_season']}")
```

---

## 📖 문서

### 개발자용
- [CLAUDE.md](CLAUDE.md) - 전체 개발 가이드
  - 실행 방법 및 테스트
  - 아키텍처 및 구조
  - 핵심 서비스 설명
  - 구현 노하우

### 사용자용
- [실행방법.md](실행방법.md) - 대시보드 사용 가이드

### 개선 보고서
- [TOP10_매핑_개선_완료_보고서.md](TOP10_매핑_개선_완료_보고서.md) - 1단계 (95.0% 달성)
- [2단계_ICD10_전체_매핑_완료_보고서.md](2단계_ICD10_전체_매핑_완료_보고서.md) - 2단계 (96.3% 달성)

### 기획 문서
- [plan/](plan/) - 프로젝트 계획 및 기획안

---

## 🔄 개발 이력

### ✅ 완료 단계

**Day 1**: 데이터 파이프라인
- 파일 파싱 (HIRA/SMC)
- 기간 분류 (비수기/통상)
- DRG 매칭 (ICD-10 + 진단명)
- 데이터 집계 (질환/의료진/진료과)
- KPI 산출 엔진

**Day 2**: HTML 대시보드
- Jinja2 템플릿 시스템
- 홈, 진료과, 의료진, 질환 뷰
- 파일 경로 기반 네비게이션
- Bootstrap 5 스타일링

**Day 3**: 데이터 연동
- 파일 업로드 API
- 세션 관리
- 동적 데이터 로딩

**매칭 개선**:
- 1단계: TOP 10 진단명 매핑 (95.0%)
- 2단계: ICD-10 전체 매핑 (96.3%)
- 데이터 필터링 (환자수 6명 미만 제외)
- UI 개선 (KPI 카드 2개로 간소화)

### 향후 개선 (선택적)
- [ ] HIRA 연간 데이터 확보 (현재: 4분기만)
- [ ] 데이터베이스 연동 (SQLite/PostgreSQL)
- [ ] 엑셀 다운로드 기능
- [ ] DRG 매핑 관리 UI
- [ ] 사용자 인증
- [ ] Docker 배포

---

## 🤝 기여하기

이 프로젝트는 선메디컬센터 내부 프로젝트입니다.

---

## 📞 문의

프로젝트 관련 문의는 적정진료관리팀으로 연락주세요.
