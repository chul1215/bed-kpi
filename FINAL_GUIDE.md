# 선메디컬센터 병상가동 KPI 산출 프로그램 - 최종 실행 가이드

## 🎉 완료 상태

**3일 개발 완료**: Day 1 (데이터 파이프라인) + Day 2 (HTML 대시보드) + Day 3 (파일 업로드 & 동적 데이터)

---

## 🚀 빠른 시작

### 1. 서버 실행

```bash
cd /Users/chul/Documents/bed-kpi/backend
python3 -m app.main
```

서버가 시작되면 다음과 같이 출력됩니다:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. 브라우저에서 접속

**Demo 모드 (샘플 데이터)**:
```
http://localhost:8000
```

**업로드 페이지**:
```
http://localhost:8000/upload
```

---

## 📋 사용 시나리오

### 시나리오 A: 샘플 데이터로 대시보드 미리보기

1. 브라우저에서 `http://localhost:8000` 접속
2. 샘플 데이터로 구성된 대시보드 확인:
   - 홈 화면: KPI 카드 + 의사별 질환 TOP 6
   - 진료과 뷰: 진료과 랭킹 + 의료진 드릴다운
   - 의료진 상세: 의료진별 KPI + 질환별 상세
   - 질환 뷰: 질환별 기준 LOS + 담당 의료진 분포

3. 병원/기간 토글 테스트:
   - [대전선병원] / [유성선병원] 전환
   - [비수기] / [통상기간] 전환

### 시나리오 B: 실제 파일 업로드 및 KPI 계산

#### Step 1: 파일 준비

필요한 파일:
- **HIRA 파일**: 심평원 ADRG별 평균재원일수 (Excel)
  - 예시: `2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx`
  - 위치: `data/hira/`

- **SMC 파일**: 선메디컬센터 내부 실적 (Excel)
  - 예시: `25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx`
  - 위치: `data/smc/`

#### Step 2: 파일 업로드

1. `http://localhost:8000/upload` 접속

2. 병원 선택:
   - [ ] 대전선병원
   - [ ] 유성선병원

3. HIRA 파일 선택:
   - "HIRA 기준 파일 (Excel)" → 파일 선택

4. SMC 파일 선택:
   - "SMC 내부 실적 파일 (Excel)" → 파일 선택

5. "📊 KPI 계산 시작" 버튼 클릭

#### Step 3: 계산 진행 확인

Progress Bar가 나타나며 다음 단계가 진행됩니다:
```
파일 업로드 중... (0-30%)
    ↓
DRG 매칭 및 데이터 집계 중... (30-60%)
    ↓
KPI 계산 중... (60-90%)
    ↓
완료! (100%)
```

#### Step 4: 결과 확인

성공 시 다음 정보가 표시됩니다:
```
✅ KPI 계산 완료!

세션 ID: abc-123-456...
병원: 대전
HIRA 기준: 739건
SMC 실적: 15,234건
DRG 매칭률: 87.5%
비수기: 5,123건 / 통상기간: 10,111건

[📈 대시보드 보기]
```

#### Step 5: 대시보드 조회

"대시보드 보기" 버튼을 클릭하면 다음 URL로 이동:
```
http://localhost:8000/?session_id=abc123&hospital=대전&period=off_season
```

실제 업로드한 데이터로 계산된 KPI가 표시됩니다.

---

## 🗂️ 페이지별 기능

### 1. 홈 화면 (`/`)

**URL**:
- Demo: `http://localhost:8000`
- 실제: `http://localhost:8000/?session_id=abc123&hospital=대전&period=off_season`

**주요 기능**:
- ✅ KPI 카드 3종:
  - 평균 LOS 갭
  - 추가 병상일수
  - 목표 가동률

- ✅ 의사별 질환 TOP 6:
  - 환자수 정렬
  - 펼침/접힘 UI
  - 질환별 상세 정보

- ✅ 핵심 인사이트:
  - 가장 어려운 질환
  - 임팩트 상위 의료진 TOP 3
  - 전체 평균 조정 필요량

### 2. 진료과 뷰 (`/department`)

**URL**:
- Demo: `http://localhost:8000/department`
- 실제: `http://localhost:8000/department?session_id=abc123&hospital=대전&period=off_season`

**주요 기능**:
- ✅ 진료과 목록 (환자수, 현 LOS, 목표 LOS, LOS 갭)
- ✅ 진료과 선택 시 의료진 드릴다운
- ✅ 의료진 상세 링크

### 3. 의료진 상세 (`/doctor`)

**URL**:
- Demo: `http://localhost:8000/doctor?name=홍길동`
- 실제: `http://localhost:8000/doctor?name=홍길동&session_id=abc123&hospital=대전&period=off_season`

**주요 기능**:
- ✅ 의료진 검색
- ✅ 의료진 KPI 카드 3종
- ✅ 질환별 KPI 상세 테이블
- ✅ 목표 달성 시 예상 변화 요약

### 4. 질환 뷰 (`/disease`)

**URL**:
- Demo: `http://localhost:8000/disease?name=폐렴`
- 실제: `http://localhost:8000/disease?name=폐렴&session_id=abc123&hospital=대전&period=off_season`

**주요 기능**:
- ✅ 질환명 검색
- ✅ HIRA 기준 LOS vs 현 LOS 비교
- ✅ 담당 의료진 분포
- ✅ 월별 LOS 추이 (비수기 구간 강조)

### 5. 업로드 페이지 (`/upload`)

**URL**: `http://localhost:8000/upload`

**주요 기능**:
- ✅ 병원 선택 (대전/유성)
- ✅ HIRA/SMC 파일 업로드
- ✅ 실시간 진행 상태 표시
- ✅ 업로드 결과 표시 (메타데이터, 세션 ID)
- ✅ 대시보드 바로가기

---

## 🔧 API 엔드포인트

### 1. 파일 업로드

**POST** `/api/upload/files`

**요청**:
```
Content-Type: multipart/form-data

- hira_file: File (Excel)
- smc_file: File (Excel)
- hospital: str ("대전" or "유성")
```

**응답**:
```json
{
  "session_id": "abc-123-456...",
  "status": "completed",
  "message": "파일 업로드 및 KPI 계산 완료",
  "metadata": {
    "hira_count": 739,
    "smc_count": 15234,
    "off_season_count": 5123,
    "normal_count": 10111,
    "match_rate": 87.5
  }
}
```

**예시 (curl)**:
```bash
curl -X POST "http://localhost:8000/api/upload/files" \
  -F "hira_file=@data/hira/hira.xlsx" \
  -F "smc_file=@data/smc/smc.xlsx" \
  -F "hospital=대전"
```

### 2. 업로드 상태 조회

**GET** `/api/upload/status/{session_id}`

**응답**:
```json
{
  "session_id": "abc-123-456...",
  "hospital": "대전",
  "status": "completed",
  "created_at": "2026-02-20T10:30:00",
  "metadata": {
    "hira_count": 739,
    "smc_count": 15234,
    "match_rate": 87.5
  }
}
```

### 3. 헬스 체크

**GET** `/health`

**응답**:
```json
{
  "status": "healthy"
}
```

---

## 📊 데이터 구조

### KPI 계산 결과

```python
{
    # 요약 KPI
    'summary_kpi': {
        'average_los_gap': 1.8,
        'total_additional_bed_days': 2834,
        'current_utilization_rate': 72.5,
        'target_utilization_rate': 83.1,
        'patient_count': 5186
    },

    # 의료진 KPI (비수기)
    'doctor_kpis_off_season': [
        {
            'doctor': '홍길동',
            'department': '내과',
            'patient_count': 420,
            'los_gap': 1.7,
            'additional_bed_days': 714,
            'total_bed_days': 3276,
            'target_los': 9.5
        },
        ...
    ],

    # 질환 KPI (비수기)
    'disease_kpis_off_season': [
        {
            'diagnosis': '폐렴',
            'patient_count': 120,
            'current_los': 8.0,
            'target_los': 10.5,
            'los_gap': 2.5,
            'additional_bed_days': 300
        },
        ...
    ],

    # 인사이트
    'insights_off_season': [
        "목표 도달이 가장 어려운 질환: 폐렴 (+3.0일)",
        "임팩트 상위 의료진 TOP3 합산 추가 병상일수: 3,220일",
        "기준치 대비 전체 평균 조정 필요량: ±1.8일"
    ]
}
```

---

## ⚙️ 설정

### 환경 변수 (`.env`)

```bash
APP_NAME="선메디컬센터 병상가동 KPI 산출 시스템"
APP_VERSION="1.0.0"
DEBUG=True
HOST="0.0.0.0"
PORT=8000

# 업로드 디렉토리
UPLOAD_DIR="./uploads"

# 병원 설정
HOSPITAL_CONFIG_DAEJEON_BED_COUNT=300
HOSPITAL_CONFIG_YUSEONG_BED_COUNT=250

# 기간 설정
OFF_SEASON_MONTHS="3,4,11,12"  # 비수기
MIN_PATIENT_COUNT=6  # 환자수 6명 미만 제외
```

### 데이터 파일 경로

```
data/
├── hira/                               # 심평원 기준 데이터
│   └── 2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx
├── smc/                                # SMC 내부 실적
│   └── 25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx
└── mapping/                            # DRG 매핑 테이블
    └── diagnosis_drg_mapping.xlsx     # (선택적, 매칭률 향상용)
```

---

## 🧪 테스트

### 통합 테스트 실행

```bash
cd backend
python3 tests/test_day3_integration.py
```

**예상 출력**:
```
================================================================================
Day 3 통합 테스트 시작
================================================================================

1. 모듈 Import 체크:
  ✓ KPIPipeline 로드 성공
  ✓ MemoryStore 로드 성공
  ✓ DashboardGenerator 로드 성공

2. KPI 파이프라인 초기화:
  ✓ file_parser: <...>
  ✓ period_classifier: <...>
  ✓ drg_matcher: <...>
  ✓ aggregator: <...>
  ✓ kpi_calculator: <...>

3. 메모리 저장소 테스트:
  ✓ 세션 생성: abc-123-...
  ✓ 세션 조회: 대전, processing
  ✓ 상태 업데이트: completed

4. 대시보드 생성기 테스트:
  ✓ index.html 로드 성공
  ✓ department.html 로드 성공
  ✓ doctor.html 로드 성공
  ✓ disease.html 로드 성공
  ✓ upload.html 로드 성공
  ✓ base.html 로드 성공
  ✓ render_upload() 성공: 25184 bytes

5. 전체 파이프라인 테스트:
  ✓ HIRA 파일 존재
  ✓ SMC 파일 존재
  ✓ 파이프라인 실행 성공
    - HIRA: 739건
    - SMC: 33853건
    - 매칭률: 87.5%
    - 비수기: 11330건
    - 통상기간: 22523건

================================================================================
테스트 결과 요약
================================================================================
✅ PASS - Import 테스트
✅ PASS - 파이프라인 초기화
✅ PASS - 메모리 저장소
✅ PASS - 대시보드 생성기
✅ PASS - 전체 파이프라인

총 5개 중 5개 통과

🎉 모든 테스트 통과!
```

---

## ⚠️ 문제 해결

### 1. 서버가 시작되지 않음

**증상**: `ModuleNotFoundError: No module named 'app'`

**해결**:
```bash
cd backend
pip3 install -r requirements.txt
```

### 2. DRG 매칭률이 낮음

**증상**: "DRG 매칭률: 50% 미만"

**해결**:
1. `data/mapping/diagnosis_drg_mapping.xlsx` 파일 생성
2. 컬럼: `diagnosis`, `drg_code_3digit`, `adrg_name`, `confidence`
3. SMC 고유 진단명과 HIRA ADRG명 수동 매핑

### 3. 파일 업로드 실패

**증상**: "500 Internal Server Error"

**확인 사항**:
- HIRA 파일 형식: Excel (.xlsx), skiprows=2 적용 가능
- SMC 파일 형식: Excel (.xlsx), Sheet1에 데이터 존재
- 필수 컬럼 존재:
  - HIRA: `4단DRG번호`, `ADRG명`, `평균재원일수`
  - SMC: `구분`, `퇴원일자`, `평균재원`, `퇴원과`, `진단명`, `의사명`

### 4. 세션 ID로 데이터 조회 안됨

**증상**: 샘플 데이터만 표시됨

**확인 사항**:
- URL에 `session_id` 파라미터 포함 여부 확인
- 서버 재시작 후 세션 데이터 손실 (in-memory 저장소)

---

## 📚 추가 참고 문서

- **Day 1 완료 보고서**: (이전 세션)
- **Day 2 완료 보고서**: `DAY2_SUMMARY.md`
- **Day 3 완료 보고서**: `DAY3_SUMMARY.md`
- **프로젝트 가이드**: `CLAUDE.md`
- **와이어프레임**: `plan/병상가동 KPI 프로그램 와이어프레임.md`
- **요구사항 명세**: `plan/병상가동 KPI 산출 프로그램 PRD.md`

---

## 🎯 핵심 기능 요약

✅ **3일 완료**:
- Day 1: 데이터 파이프라인 (파싱, 집계, KPI 계산)
- Day 2: HTML 대시보드 (와이어프레임 100% 구현)
- Day 3: 파일 업로드 & 동적 데이터 연동

✅ **주요 기능**:
- 파일 업로드 (HIRA + SMC)
- 자동 기간 분류 (비수기/통상기간)
- DRG 매칭 (퍼지 매칭 + 수동 매핑)
- KPI 계산 (질환/의료진/진료과)
- 대시보드 (홈/진료과/의료진/질환)
- 세션 관리 (UUID 기반)
- 동적 데이터 로딩 (session_id)

✅ **정합성 검증**:
- 진료과 합계 = 의료진 합계
- 비수기 + 통상기간 = SMC 전체
- LOS 갭 양방향 유지

---

## 🚀 다음 단계 (선택적)

1. **데이터베이스 연동**:
   - SQLite 또는 PostgreSQL
   - 세션 영구 저장
   - 과거 업로드 이력 조회

2. **엑셀 다운로드**:
   - 요약 KPI 엑셀
   - 의사별 TOP 6 엑셀
   - 진료과별/질환별 상세 엑셀

3. **DRG 매핑 관리 UI**:
   - 수동 매핑 추가/수정
   - 매핑 통계 조회
   - 퍼지 매칭 신뢰도 조정

4. **배포**:
   - Docker 컨테이너화
   - Nginx 리버스 프록시
   - HTTPS 설정

---

## 📞 지원

문제 발생 시:
1. `backend/logs/` 폴더의 로그 파일 확인
2. `python3 tests/test_day3_integration.py` 테스트 실행
3. 브라우저 개발자 도구 (F12) 콘솔 확인

---

## ✨ 완료!

**선메디컬센터 병상가동 KPI 산출 시스템**이 정상적으로 구동되고 있습니다. 🎉

파일을 업로드하고 실제 KPI를 확인해보세요!

```
http://localhost:8000/upload
```
