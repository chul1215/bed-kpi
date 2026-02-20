# 병상가동 KPI 산출 프로그램

선메디컬센터(대전선병원/유성선병원) 시기별 병상가동 KPI 산출 웹 대시보드

## 📋 프로젝트 개요

### 목적
- 심평원 기준 재원일수 대비 자체 재원일수 격차를 정량화
- 비수기(3-4월, 11-12월) / 통상기간(1-2월, 5-10월) 분리 관리
- 진료과-의료진-질환 단위 목표 관리 체계 구축

### 기술 스택
- **Backend**: Python 3.9+ (FastAPI, pandas, SQLite)
- **Frontend**: React + TypeScript + Ant Design (예정)
- **Data Processing**: pandas, openpyxl
- **Deployment**: Docker (로컬 실행)

---

## 🚀 빠른 시작

### 백엔드 설정

```bash
# 1. 의존성 설치
cd backend
pip3 install -r requirements.txt

# 2. 서버 실행
python3 -m app.main
# 또는
uvicorn app.main:app --reload --port 8000
```

서버는 `http://localhost:8000`에서 실행됩니다.

### 테스트

```bash
# 파일 파서 테스트
cd backend
python3 -c "
from app.services.file_parser import FileParser
hira_df = FileParser.parse_hira_file('../data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx')
smc_df = FileParser.parse_smc_file('../data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx')
print(f'HIRA: {len(hira_df)}건, SMC: {len(smc_df)}건')
print(f'검증 통과: {FileParser.validate_files(hira_df, smc_df)[0]}')
"
```

---

## 📁 프로젝트 구조

```
bed-kpi/
├── backend/                    # Python FastAPI 백엔드
│   ├── app/
│   │   ├── main.py            # FastAPI 앱 진입점
│   │   ├── config.py          # 설정 관리
│   │   ├── models/            # Pydantic 데이터 모델
│   │   ├── services/          # 비즈니스 로직
│   │   │   ├── file_parser.py         # HIRA/SMC 파일 파싱 ✅
│   │   │   ├── period_classifier.py   # 기간 분류 ✅
│   │   │   ├── drg_matcher.py         # DRG 매칭 (예정)
│   │   │   ├── aggregator.py          # 데이터 집계 (예정)
│   │   │   └── kpi_calculator.py      # KPI 산출 (예정)
│   │   ├── api/               # API 라우터 (예정)
│   │   ├── database/          # DB 스키마 (예정)
│   │   └── utils/
│   ├── tests/                 # 단위 테스트 (예정)
│   └── requirements.txt        # 의존성
│
├── frontend/                  # React + TypeScript (예정)
│   ├── src/
│   ├── public/
│   └── package.json
│
├── data/
│   ├── hira/                  # 심평원 기준 데이터
│   ├── smc/                   # SMC 내부 실적 데이터
│   └── mapping/               # DRG 매핑 테이블 (예정)
│
├── plan/                      # 프로젝트 계획 문서 (Obsidian vault)
│   ├── 병상가동 KPI 산출 프로그램 PRD.md
│   ├── 선메디컬센터 시기별 병상가동 KPI 산출 프로그램 기획안.md
│   └── 병상가동 KPI 프로그램 와이어프레임.md
│
├── CLAUDE.md                  # Claude Code 개발 가이드
├── README.md                  # 이 파일
└── .gitignore
```

---

## 📊 핵심 개념

### KPI 산출 공식

```python
# 현재 재원일수
current_los = 병상일수 / 환자수

# LOS 갭 (양방향 유지)
los_gap = HIRA_목표_LOS - 현재_LOS
# 양수: 늘려야 함, 음수: 줄여야 함

# 추가 병상일수 (임팩트)
additional_bed_days = los_gap × 환자수

# 의료진 목표 LOS (가중 평균)
doctor_target_los = Σ(질환_목표_LOS × 질환_환자수_비중)
```

### 기간 구분
- **비수기**: 3월, 4월, 11월, 12월
- **통상기간**: 1월, 2월, 5월, 6월, 7월, 8월, 9월, 10월

---

## 🔄 개발 단계

### Phase 1: 데이터 파이프라인 (진행 중)
- [x] 프로젝트 초기화
- [x] 파일 파서 (HIRA, SMC)
- [x] 기간 분류
- [ ] 데이터베이스 스키마
- [ ] DRG 매칭
- [ ] 데이터 집계
- [ ] KPI 산출

### Phase 2-6: 후속 개발 (예정)
- KPI 조회 API
- 브리핑용 리포트 생성
- 운영 대시보드 (검색, 드릴다운)
- 프론트엔드 구현
- 배포

상세 계획: [`/Users/chul/.claude/plans/magical-soaring-blossom.md`](/Users/chul/.claude/plans/magical-soaring-blossom.md)

---

## 📖 개발 가이드

전체 개발 가이드는 [CLAUDE.md](CLAUDE.md)를 참조하세요:
- 실행 방법 및 테스트
- 아키텍처 및 구조
- 핵심 서비스 설명
- 일반적인 작업 방법
- 데이터 일관성 규칙

---

## 🧪 테스트

### 파일 파싱 테스트

```bash
cd backend
python3 -c "
from app.services.file_parser import FileParser

# HIRA 파싱
hira_df = FileParser.parse_hira_file('../data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx')
assert len(hira_df) > 700, f'HIRA 데이터 부족: {len(hira_df)}건'

# SMC 파싱
smc_df = FileParser.parse_smc_file('../data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx')
assert len(smc_df) > 30000, f'SMC 데이터 부족: {len(smc_df)}건'

# 검증
is_valid, msg = FileParser.validate_files(hira_df, smc_df)
assert is_valid, f'검증 실패: {msg}'

print('✅ 모든 테스트 통과!')
"
```

---

## 📝 데이터 명세

### HIRA 파일 (심평원 기준)
- **파일명**: `2025_4분기_종합병원_ADRG별_평균재원)_*.xlsx`
- **데이터**: 739건 (DRG별 평균재원일수)
- **컬럼**: 4단DRG번호, ADRG명, 평균재원일수

### SMC 파일 (내부 실적)
- **파일명**: `25년도 대전, 유성 의사별 퇴원진단*.xlsx`
- **데이터**: 33,853건 (개별 환자 레벨)
- **컬럼**: 구분(병원), 퇴원일자, 평균재원, 퇴원과, 진단명, 의사명

---

## 🤝 기여하기

이 프로젝트는 선메디컬센터 내부 프로젝트입니다.

---

## 📜 라이선스

내부 사용 전용

---

## 📞 문의

프로젝트 관련 문의는 적정진료관리팀으로 연락주세요.
