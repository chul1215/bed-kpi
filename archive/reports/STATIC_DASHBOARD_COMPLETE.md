# 정적 HTML 대시보드 생성 완료 ✅

## 🎉 구현 완료

**서버 없이 바로 GitHub Pages로 배포 가능한 정적 HTML 대시보드 생성!**

### 변경 사항

#### 1. KPI 계산기 수정 ([kpi_calculator.py](backend/app/services/kpi_calculator.py))

의료진별 KPI 계산 시 `department` 필드 반환 추가:

```python
def calculate_doctor_kpi(...):
    # ...
    return {
        'doctor': doctor_name,
        'department': doctor_row.get('department', ''),  # ✅ 추가
        'patient_count': patient_count,
        # ...
    }
```

#### 2. 대시보드 생성기 수정 ([dashboard_generator.py](backend/app/services/dashboard_generator.py))

DataFrame을 리스트로 변환하여 Jinja2 템플릿 호환성 확보:

```python
def render_department(...):
    # DataFrame을 리스트로 변환
    doctor_kpis_by_dept_list = {}
    for dept, df in doctor_kpis_by_dept.items():
        doctor_kpis_by_dept_list[dept] = self._format_dataframe(df)
```

NaN 값 처리:

```python
def _prepare_doctor_disease_data(...):
    import pandas as pd
    if pd.isna(patient_count):
        patient_count = 0
    if pd.isna(los_gap):
        los_gap = 0
    # ...
```

#### 3. Jinja2 템플릿 수정 (HTML 템플릿)

None 값 안전하게 처리:

```jinja2
{% if doctor.los_gap is not none %}
    {% if doctor.los_gap >= 0 %}
        <span class="positive">+{{ "%.1f"|format(doctor.los_gap) }}일</span>
    {% else %}
        <span class="negative">{{ "%.1f"|format(doctor.los_gap) }}일</span>
    {% endif %}
{% else %}
    <span style="color: #95a5a6;">-</span>
{% endif %}
```

#### 4. 정적 HTML 생성 스크립트 ([generate_static_dashboard.py](generate_static_dashboard.py))

병원별/기간별로 모든 페이지 사전 생성:

- 홈 화면 (KPI 카드 + 의사별 질환 TOP 6)
- 진료과 뷰 (진료과 랭킹 + 드릴다운)
- 의료진 상세 (상위 10명)
- 질환 뷰 (상위 10개)

---

## 📁 생성된 파일 구조

```
docs/
├── index.html                             # 리디렉션 (→ 대전/index_off_season.html)
├── README.md                              # 배포 가이드
├── 대전/
│   ├── index_off_season.html             # 홈 (비수기)
│   ├── index_normal.html                 # 홈 (통상기간)
│   ├── department_off_season.html        # 진료과 뷰 (비수기)
│   ├── department_normal.html            # 진료과 뷰 (통상기간)
│   ├── doctors_off_season/               # 의료진 상세 (비수기, 10명)
│   │   ├── 김광민.html
│   │   ├── 나운태.html
│   │   └── ...
│   ├── doctors_normal/                   # 의료진 상세 (통상기간, 10명)
│   ├── diseases_off_season/              # 질환 뷰 (비수기, 10개)
│   └── diseases_normal/                  # 질환 뷰 (통상기간, 10개)
└── 유성/
    └── (대전과 동일 구조)
```

**총 생성 파일:**
- 대전: 44개 HTML 파일
- 유성: 44개 HTML 파일
- 루트: 2개 (index.html, README.md)
- **합계: 90개 HTML 파일**

---

## 🚀 사용 방법

### 1. 정적 HTML 생성

```bash
# 프로젝트 루트에서 실행
python3 generate_static_dashboard.py
```

**출력:**
```
================================================================================
정적 HTML 대시보드 생성 시작
================================================================================

파일 로드:
  - HIRA: 2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx
  - SMC: 25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx

================================================================================
대전선병원 데이터 처리 시작
================================================================================

✅ KPI 계산 완료:
  - HIRA: 739건
  - SMC: 15514건
  - 비수기: 5186건
  - 통상기간: 10328건

비수기 HTML 생성 중...
  ✓ index_off_season.html
  ✓ department_off_season.html
  ✓ doctors_off_season/ (10명)
  ✓ diseases_off_season/ (10개)

통상기간 HTML 생성 중...
  ✓ index_normal.html
  ✓ department_normal.html
  ✓ doctors_normal/ (10명)
  ✓ diseases_normal/ (10개)

✅ 대전선병원 HTML 생성 완료

================================================================================
유성선병원 데이터 처리 시작
================================================================================
(유성 동일 프로세스...)

✅ 유성선병원 HTML 생성 완료

✓ docs/index.html (리디렉션)
✓ docs/README.md

================================================================================
정적 HTML 대시보드 생성 완료!
================================================================================
```

### 2. 로컬에서 미리보기

```bash
# Python 내장 웹서버 사용
cd docs
python3 -m http.server 8080

# 브라우저에서 접속
# http://localhost:8080
```

### 3. GitHub Pages 배포

#### Step 1: GitHub 저장소에 커밋

```bash
git add docs/
git commit -m "Add static HTML dashboard for GitHub Pages"
git push origin main
```

#### Step 2: GitHub Pages 설정

1. GitHub 저장소 페이지 이동
2. **Settings** 클릭
3. 왼쪽 메뉴에서 **Pages** 클릭
4. **Source** 섹션:
   - Branch: `main` 선택
   - Folder: `/docs` 선택
5. **Save** 클릭

#### Step 3: 배포 확인

약 1-2분 후 다음 URL에서 접속 가능:

```
https://<username>.github.io/<repository-name>/
```

예시:
```
https://chul.github.io/bed-kpi/
```

---

## 📊 데이터 업데이트 방법

### 새로운 데이터로 대시보드 재생성

1. `data/hira/` 폴더에 최신 HIRA 파일 복사
2. `data/smc/` 폴더에 최신 SMC 파일 복사
3. `backend/app/config.py` 파일 경로 업데이트:

```python
# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 사전 식립 데이터 경로
PRELOADED_HIRA_FILE: Path = PROJECT_ROOT / "data/hira/<새로운_파일명>.xlsx"
PRELOADED_SMC_FILE: Path = PROJECT_ROOT / "data/smc/<새로운_파일명>.xlsx"
```

4. 정적 HTML 재생성:

```bash
python3 generate_static_dashboard.py
```

5. GitHub에 커밋 및 푸시:

```bash
git add docs/ backend/app/config.py
git commit -m "Update dashboard data (YYYY-MM-DD)"
git push origin main
```

**GitHub Pages가 자동으로 최신 버전 배포!**

---

## 🎯 주요 특징

### 1. 서버 불필요
- ✅ FastAPI/uvicorn 서버 실행 불필요
- ✅ Python 런타임 불필요 (배포 후)
- ✅ GitHub Pages로 무료 호스팅

### 2. 완전한 기능
- ✅ KPI 카드 3종 (평균 LOS 갭, 추가 병상일수, 목표 가동률)
- ✅ 의사별 질환 TOP 6 랭킹
- ✅ 진료과 뷰 (드릴다운)
- ✅ 의료진 상세 (상위 10명)
- ✅ 질환 뷰 (상위 10개)
- ✅ 병원 토글 (대전 ↔ 유성)
- ✅ 기간 토글 (비수기 ↔ 통상기간)

### 3. 대용량 데이터 처리
- ✅ HIRA: 739건
- ✅ SMC 대전: 15,514건
- ✅ SMC 유성: 18,339건
- ✅ 총 33,853건 환자 데이터

### 4. 반응형 디자인
- ✅ Bootstrap 5 기반
- ✅ 모바일/태블릿/데스크톱 지원
- ✅ 인쇄 최적화

---

## 🔧 기술 스택

### 데이터 처리
- Python 3.9+
- pandas (데이터 집계)
- openpyxl (엑셀 파싱)

### HTML 생성
- Jinja2 (템플릿 엔진)
- Bootstrap 5 (UI 프레임워크)
- Plotly.js (차트 라이브러리)

### 배포
- GitHub Pages (무료 정적 호스팅)
- Git (버전 관리)

---

## 📝 문서

### 생성된 README.md

`docs/README.md` 파일에 다음 내용 포함:

- 페이지 구조
- 대전/유성 병원별 링크
- 배포 방법
- GitHub Pages 설정 가이드

### CLAUDE.md 업데이트 필요

다음 섹션 추가 권장:

```markdown
## Static HTML Generation

### Generate Static Dashboard

\`\`\`bash
python3 generate_static_dashboard.py
\`\`\`

### Deploy to GitHub Pages

1. Commit docs/ folder
2. Push to GitHub
3. Settings > Pages > Source: main branch, /docs folder
4. Access: https://<username>.github.io/<repository>/
```

---

## ✅ 최종 결과

### 성공적으로 완료된 항목

- [x] KPI 계산기 department 필드 반환
- [x] 대시보드 생성기 DataFrame → 리스트 변환
- [x] Jinja2 템플릿 None 값 안전 처리
- [x] 정적 HTML 생성 스크립트 구현
- [x] 대전/유성 병원별 HTML 생성 (각 44개 파일)
- [x] 비수기/통상기간별 HTML 생성
- [x] 리디렉션 index.html 생성
- [x] README.md 배포 가이드 생성
- [x] 전체 90개 HTML 파일 생성 완료

### 배포 준비 완료

✅ **docs/ 폴더를 GitHub에 커밋하면 즉시 배포 가능!**

```bash
git add docs/
git commit -m "Add static HTML dashboard for GitHub Pages deployment"
git push origin main
```

---

## 🎉 다음 단계

1. **GitHub Pages 배포**
   - docs/ 폴더 커밋
   - Settings > Pages 설정
   - URL 확인

2. **데이터 주기적 업데이트**
   - 새로운 HIRA/SMC 파일 추가
   - generate_static_dashboard.py 재실행
   - Git 커밋/푸시

3. **사용자 교육**
   - 대시보드 사용 방법
   - 페이지 네비게이션
   - KPI 해석 가이드

---

**🚀 서버 없이 바로 GitHub Pages로 배포 가능한 대시보드가 완성되었습니다!**
