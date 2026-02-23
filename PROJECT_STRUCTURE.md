# 프로젝트 구조

## 루트 디렉토리

```
bed-kpi/
├── 📄 CLAUDE.md                              # 개발 가이드
├── 📄 README.md                              # 프로젝트 개요
├── 📄 실행방법.md                             # 사용자 가이드
├── 📄 .gitignore                             # Git 제외 파일
│
├── 📊 보고서
│   ├── TOP10_매핑_개선_완료_보고서.md         # 1단계 (95.0%)
│   └── 2단계_ICD10_전체_매핑_완료_보고서.md   # 2단계 (96.3%) 최종
│
├── 🔧 실행 스크립트
│   ├── generate_static_dashboard.py         # 정적 대시보드 생성 ⭐
│   ├── add_top10_mappings.py                # TOP 10 매핑 추가
│   └── add_all_icd10_mappings.py            # ICD-10 전체 매핑
│
├── 📁 backend/                               # Python 백엔드
├── 📁 data/                                  # 데이터 파일
├── 📁 docs/                                  # 정적 HTML (88개)
├── 📁 plan/                                  # 기획 문서
├── 📁 archive/                               # 개발 히스토리
└── 📁 frontend/                              # React (미사용)
```

## Backend 구조

```
backend/app/
├── main.py                                   # FastAPI 앱
├── config.py                                 # 설정
│
├── services/                                 # 비즈니스 로직 ✅
│   ├── file_parser.py                        # 파일 파싱
│   ├── period_classifier.py                  # 기간 분류
│   ├── kdrg_matcher.py                       # DRG 매칭
│   ├── aggregator.py                         # 데이터 집계
│   ├── kpi_calculator.py                     # KPI 산출
│   ├── kpi_pipeline.py                       # 통합 파이프라인
│   └── hospital_summary_parser.py            # ICD-10 파싱
│
├── templates/                                # Jinja2 템플릿
│   ├── base.html                             # 공통 레이아웃
│   ├── index.html                            # 홈 (KPI 2개 + TOP 6)
│   ├── department.html                       # 진료과
│   ├── doctor.html                           # 의료진 상세
│   └── disease.html                          # 질환 상세
│
└── api/                                      # API 라우터
```

## Data 구조

```
data/
├── hira/                                     # 심평원 데이터
│   └── 2025_4분기_종합병원_ADRG별_평균재원)_*.xlsx  (739건)
│
├── smc/                                      # 병원 데이터
│   └── 25년도 대전, 유성 의사별 퇴원진단*.xlsx     (8,063건)
│
└── mapping/                                  # 매핑 테이블
    ├── icd10_to_adrg_from_kdrg46.xlsx        # ICD-10 자동 (282개)
    ├── diagnosis_kdrg44_mapping.xlsx         # 진단명 수동 (164개)
    └── KDRG 버전4.4_질병군명칭_*.xlsx        # KDRG 테이블
```

## Docs 구조 (GitHub Pages)

```
docs/
├── index.html                                # 메인 리디렉션
├── README.md                                 # 배포 가이드
│
├── 대전/                                     # 대전선병원 (44개)
│   ├── index_off_season.html                 # 비수기 홈
│   ├── index_normal.html                     # 통상 홈
│   ├── department_off_season.html
│   ├── department_normal.html
│   ├── doctors_off_season/*.html             # 의사 10명
│   ├── doctors_normal/*.html                 # 의사 10명
│   ├── diseases_off_season/*.html            # 질환 10개
│   └── diseases_normal/*.html                # 질환 10개
│
└── 유성/                                     # 유성선병원 (44개)
    └── (동일 구조)
```

## Archive 구조

```
archive/
├── README.md                                 # 아카이브 가이드
│
├── reports/                                  # 중간 보고서 (30개)
│   ├── DAY2_SUMMARY.md
│   ├── DAY3_SUMMARY.md
│   ├── STATIC_DASHBOARD_COMPLETE.md
│   └── ...
│
├── scripts/                                  # 일회성 스크립트 (9개)
│   ├── analyze_all_doctors.py
│   ├── test_icd10_matching.py
│   └── ...
│
└── old_docs/                                 # 구버전 문서 (2개)
    ├── FINAL_GUIDE.md
    └── FINAL_GUIDE_2026-02-20.md
```

## 주요 파일 크기

- **Backend 코드**: ~50 파일
- **정적 HTML**: 88 파일
- **데이터 파일**: 3 파일 (엑셀)
- **매핑 테이블**: 3 파일
- **문서**: ~40 파일 (루트 3개 + 아카이브 37개)

## 실행 파일 우선순위

1. **`generate_static_dashboard.py`** ⭐ - 정적 대시보드 생성 (주요)
2. `add_top10_mappings.py` - 1단계 매핑 개선
3. `add_all_icd10_mappings.py` - 2단계 매핑 개선
4. `backend/app/main.py` - FastAPI 서버 (개발용)
