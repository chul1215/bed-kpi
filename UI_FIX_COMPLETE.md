# UI 수정사항 적용 완료

**작업 일자:** 2026-02-22
**프로젝트:** 선메디컬센터 병상가동 KPI 산출 프로그램

---

## ✅ 완료된 수정사항

### 1. NaN 값 표시 문제 해결 ✅

**문제:**
- los_gap, additional_bed_days가 NaN으로 표시됨
- 매칭된 질환이 없는 의료진의 경우 target_los가 0이 되어 계산 오류 발생

**해결:**
- `backend/app/services/kpi_calculator.py` 수정
- 매칭된 환자가 없을 때 (`total_matched == 0`) None 반환하도록 변경
- 템플릿에서 None 값을 "N/A"로 표시

```python
# kpi_calculator.py
if total_matched == 0 or weighted_target_los == 0:
    return {
        'target_los': None,
        'los_gap': None,
        'additional_bed_days': None,
        'status': 'no_target_los'
    }
```

### 2. 용어 변경 ✅

**변경 전:** 추가 병상일수
**변경 후:** 추가 재원일수

**적용 위치:**
- KPI 카드 라벨
- 테이블 헤더 (의료진 랭킹 TOP 6)
- 검색 결과 테이블

### 3. 랭킹 뷰 개선 ✅

**추가된 기능:**

#### (1) 순위 컬럼 추가
- 의료진 랭킹 TOP 6 테이블에 순위 컬럼 추가
- 임팩트 기준 (additional_bed_days) 내림차순 정렬

#### (2) 진료과 / 의료진 검색 섹션
- 랭킹 테이블 아래에 검색 기능 추가
- 진료과 드롭다운 선택 (전체 진료과 옵션 포함)
- 의료진 이름 검색 입력창
- 실시간 필터링 기능 (JavaScript)

**검색 기능 특징:**
- 진료과와 의료진 이름으로 동시 필터링 가능
- 검색 결과 최대 20명 표시
- None 값은 "N/A"로 표시
- 양수/음수 색상 구분 (청록색/빨강색)

```javascript
// 검색 로직
const allDoctors = {{ doctor_all_data|tojson|safe }};

function filterDoctors() {
    const department = document.getElementById('departmentSelect').value;
    const search = document.getElementById('doctorSearch').value.toLowerCase();

    let filtered = allDoctors;

    if (department) {
        filtered = filtered.filter(d => d.department === department);
    }

    if (search) {
        filtered = filtered.filter(d => d.doctor.toLowerCase().includes(search));
    }

    displayResults(filtered);
}
```

---

## 📁 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/services/kpi_calculator.py` | NaN 처리 로직 추가 (None 반환) |
| `backend/app/services/dashboard_generator.py` | doctor_all_data, department_list 전달 |
| `backend/app/templates/index.html` | 용어 변경, 순위 컬럼, 검색 기능 추가 |
| `docs/**/*.html` | 정적 HTML 재생성 (88개 파일) |

---

## 🚀 생성된 파일

```
docs/
├── index.html                          # 자동 리디렉션 (대전 비수기)
├── 대전/
│   ├── index_off_season.html          # ✅ 수정 완료
│   ├── index_normal.html              # ✅ 수정 완료
│   ├── department_off_season.html
│   ├── department_normal.html
│   ├── doctors_off_season/            # 10명
│   ├── doctors_normal/                # 10명
│   ├── diseases_off_season/           # 10개
│   └── diseases_normal/               # 10개
└── 유성/
    └── (대전과 동일 구조)
```

**총 파일 수:** 88개 HTML 파일

---

## 📊 실행 결과

### 대전선병원 (4분기)
- **총 환자:** 3,740명
- **비수기 (11-12월):** 2,557명
- **통상기간 (10월):** 1,183명

### 유성선병원 (4분기)
- **총 환자:** 4,323명
- **비수기 (11-12월):** 2,997명
- **통상기간 (10월):** 1,326명

---

## ✅ 검증 체크리스트

- [x] NaN 값 → None → "N/A" 표시
- [x] "추가 병상일수" → "추가 재원일수" 용어 변경
- [x] 순위 컬럼 추가 (1~6)
- [x] 진료과 선택 드롭다운
- [x] 의료진 검색 입력창
- [x] 실시간 필터링 JavaScript 작동
- [x] 검색 결과 테이블 렌더링
- [x] None 값 안전 처리 (JS 포함)
- [x] 정적 HTML 재생성 (88개 파일)

---

## 🎯 주요 개선 사항

### Before (이전)
```
의료진 랭킹 TOP 6
┌────────┬───────┬─────┬────────┬──────┐
│ 의료진 │ 진료과 │ 환자수 │ LOS 갭 │ NaN  │
└────────┴───────┴─────┴────────┴──────┘
```

### After (현재)
```
의료진 랭킹 TOP 6 (임팩트 기준)
┌────┬────────┬───────┬─────┬────────┬──────────┐
│순위│ 의료진 │ 진료과 │ 환자수 │ LOS 갭 │ 추가재원일수 │
├────┼────────┼───────┼─────┼────────┼──────────┤
│ 1  │ 홍길동 │  내과  │ 420 │  2.10  │   882    │
│ 2  │ 이순신 │ 정형과 │ 380 │  1.80  │   684    │
│ 3  │ 강감찬 │ 신경과 │ 350 │  N/A   │   N/A    │
└────┴────────┴───────┴─────┴────────┴──────────┘

진료과 / 의료진 검색
┌─────────────────────┬──────────────────────┐
│ 진료과 선택          │ 의료진 검색           │
│ [전체 진료과 ▼]      │ [이름으로 검색...]   │
└─────────────────────┴──────────────────────┘

검색 결과
┌────────┬───────┬─────┬────────┬──────────┐
│ 의료진 │ 진료과 │ 환자수 │ LOS 갭 │ 추가재원일수 │
│ (필터링된 결과)                              │
└────────┴───────┴─────┴────────┴──────────┘
```

---

## 🌐 실행 방법

### 방법 1: 파일 더블클릭 (권장)
```bash
open /Users/chul/Documents/bed-kpi/docs/index.html
```

### 방법 2: 웹서버 실행
```bash
cd /Users/chul/Documents/bed-kpi/docs
python3 -m http.server 8080
# http://localhost:8080 접속
```

### 방법 3: GitHub Pages
1. `docs/` 폴더 커밋 후 푸시
2. GitHub Settings > Pages > Source: main branch, /docs folder
3. URL: `https://<username>.github.io/<repository>/`

---

## 🔄 데이터 업데이트 시

```bash
# 1. 새 데이터 파일 복사 (data/hira/, data/smc/)
# 2. 정적 HTML 재생성
python3 generate_static_dashboard.py

# 3. docs/ 폴더 확인
open docs/index.html
```

---

**작성자:** Claude Sonnet 4.5
**최종 업데이트:** 2026-02-22 19:00

**참고 문서:**
- [ICD10_MATCHING_COMPLETE.md](ICD10_MATCHING_COMPLETE.md) - ICD-10 매칭 개선 (76%)
- [UI_UPDATE_COMPLETE.md](UI_UPDATE_COMPLETE.md) - 다크 테마 적용
- [실행방법.md](실행방법.md) - 사용자 가이드
