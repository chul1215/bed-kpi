# ADRG 기반 KPI 시스템 전환 완료 보고서

작성일: 2026-02-23

## 📊 요약

병원 자료를 **심평원 ADRG 코드 기준**으로 성공적으로 전환했습니다.

### 주요 성과

| 항목 | 기존 (진단명) | 전환 후 (ADRG) | 개선율 |
|-----|------------|--------------|-------|
| 매칭률 | 7% | **58.1%** | **8.3배** |
| 대전 비수기 ADRG | 23개 | **82개** | 3.6배 |
| 대전 비수기 환자 커버리지 | 185명 | **1,464명** | 7.9배 |
| 매핑 테이블 | 282개 (ICD-10만) | **414개** | 1.5배 |

## 🎯 전환 목표 달성

✅ **목표 1**: 심평원 ADRG 코드를 기준으로 병원 데이터 재구조화
✅ **목표 2**: 매칭률 50% 이상 달성 (실제: **58.1%**)
✅ **목표 3**: 전체 파이프라인 ADRG 기반 재작성
✅ **목표 4**: 정적 HTML 대시보드 재생성

## 📁 생성된 주요 파일

### 1. 핵심 서비스 (backend/app/services/)

| 파일 | 설명 |
|------|------|
| **adrg_mapper.py** | ADRG 코드 매핑 엔진 (신규) |
| **file_parser.py** | HIRA/SMC 파싱 (ADRG 자동 매핑 포함) |
| **aggregator.py** | ADRG 기반 집계 함수 추가 |
| **kpi_calculator.py** | ADRG 기반 KPI 계산 함수 추가 |

### 2. 매핑 데이터 (data/mapping/)

| 파일 | 설명 | 개수 |
|------|------|------|
| **icd10_to_adrg_from_kdrg46.xlsx** | ICD-10 자동 매핑 | 282개 |
| **diagnosis_adrg_mapping.xlsx** | 진단명 수동 매핑 | 132개 |
| **adrg_mapping_template.xlsx** | 미매칭 진단명 TOP 100 | - |

### 3. 대시보드 (docs/)

| 파일 | 설명 |
|------|------|
| **index.html** | 메인 대시보드 (병원/기간 선택) |
| **대전/kpi_data_off_season.json** | 대전 비수기 KPI 데이터 |
| **대전/kpi_data_normal.json** | 대전 통상기간 KPI 데이터 |
| **유성/kpi_data_off_season.json** | 유성 비수기 KPI 데이터 |
| **유성/kpi_data_normal.json** | 유성 통상기간 KPI 데이터 |

### 4. 테스트 스크립트

| 파일 | 설명 |
|------|------|
| **test_adrg_pipeline.py** | ADRG 파이프라인 전체 테스트 |
| **generate_adrg_dashboard.py** | ADRG 기반 대시보드 생성 |
| **convert_diagnosis_to_adrg_mapping.py** | 기존 매핑 변환 도구 |

## 🔧 구현 상세

### ADRG 매핑 전략

**3단계 매칭 우선순위:**
1. **ICD-10 자동 매핑** (최우선): KDRG 4.6 코드 기반
2. **진단명 수동 매핑**: 기존 339개 → 132개 변환
3. **진단명 직접/부분 일치**: ADRG명과 진단명 비교

### 매칭 성과 (전체 데이터)

- **총 환자**: 8,063명
- **매칭 환자**: 4,688명 (**58.1%**)
- **미매칭**: 3,375명 (41.9%)

### 병원별 × 기간별 상세 결과

#### 대전선병원

| 기간 | 환자수 | ADRG 수 | 의료진 | 추가 재원일수 | 가동률 개선 |
|------|--------|---------|--------|---------------|------------|
| 비수기 | 2,557명 | 82개 | 41명 | +154일 | +0.4% |
| 통상기간 | 1,183명 | 70개 | 41명 | -95일 | -0.1% |

**의료진 매칭률 (비수기 TOP 5):**
- 정윤화: 75.7% (187/247)
- 조남열: 51.7% (75/145)
- 나운태: 53.6% (74/138)
- 최동진: 54.7% (47/86)
- 이봉주: 90.7% (78/86)

#### 유성선병원

| 기간 | 환자수 | ADRG 수 | 의료진 | 추가 재원일수 | 가동률 개선 |
|------|--------|---------|--------|---------------|------------|
| 비수기 | 2,997명 | 77개 | 53명 | +1,529일 | +5.0% |
| 통상기간 | 1,326명 | 63개 | 50명 | +941일 | +1.5% |

**의료진 매칭률 (비수기 TOP 5):**
- 전재균: 97.2% (70/72)
- 권순행: 92.8% (77/83)
- 박건우: 89.0% (258/290)
- 이연선: 90.2% (37/41)
- 박기용: 88.2% (15/17)

### TOP ADRG (대전 비수기)

| ADRG 코드 | ADRG명 | 환자수 | LOS 갭 | 추가 병상일수 |
|-----------|--------|--------|--------|--------------|
| Z630 | 기타 추적관리 | 177명 | +7.42일 | +1,313일 |
| G521 | 결장경 시술 | 164명 | +1.72일 | +282일 |
| I164 | 기타 슬관절 수술 | 136명 | -3.99일 | -543일 |
| Z620 | 치료 완결후 추적관리 | 60명 | -0.60일 | -36일 |
| B684 | 허혈 뇌졸중 | 54명 | -1.92일 | -104일 |

## 📚 기술 문서

### API 변경사항

#### 기존 (진단명 기반)
```python
# 집계
disease_agg = Aggregator.aggregate_by_disease(df)
doctor_disease_agg = Aggregator.aggregate_by_doctor_disease(df)

# KPI 계산
disease_kpi = KPICalculator.calculate_disease_kpi(row)
doctor_kpi = KPICalculator.calculate_doctor_kpi(
    row, disease_target_map, doctor_disease_df
)
```

#### 신규 (ADRG 기반)
```python
# 집계
adrg_agg = Aggregator.aggregate_by_adrg(df)
doctor_adrg_agg = Aggregator.aggregate_by_doctor_adrg(df)

# KPI 계산
adrg_kpi = KPICalculator.calculate_adrg_kpi(row)
doctor_kpi = KPICalculator.calculate_doctor_kpi_by_adrg(
    row, adrg_target_map, doctor_adrg_df
)
```

### 하위 호환성

기존 진단명 기반 함수는 **별칭(alias)**으로 유지:
- `aggregate_by_disease` → `aggregate_by_diagnosis` (내부)
- `calculate_disease_kpi` → `calculate_diagnosis_kpi` (내부)

## 🚀 배포 방법

### 로컬 테스트

```bash
# ADRG 파이프라인 테스트
python3 test_adrg_pipeline.py

# 대시보드 재생성
python3 generate_adrg_dashboard.py

# 로컬 확인
open docs/index.html
```

### GitHub Pages 배포

```bash
git add docs/ data/mapping/ backend/app/services/
git commit -m "feat: ADRG 기반 KPI 시스템 전환 (매칭률 58.1%)"
git push origin main

# GitHub Settings > Pages > Source: main branch, /docs folder
```

## 📈 향후 개선 방향

### 1. 매칭률 추가 개선 (58% → 80%+)

**현재 미매칭 TOP 진단명 확인:**
```bash
open data/mapping/adrg_mapping_template.xlsx
```

**개선 방법:**
- 미매칭 진단명 TOP 100에 ADRG 코드 수동 매핑
- `diagnosis_adrg_mapping.xlsx`에 추가
- 대시보드 재생성

### 2. 동적 대시보드 구현

**현재 (정적 JSON):**
- 병원/기간별 JSON 파일 생성
- JavaScript로 로딩하여 표시

**향후 (FastAPI):**
- 실시간 파일 업로드
- 동적 KPI 계산
- 인터랙티브 차트

### 3. 데이터베이스 연동

```python
# SQLite/PostgreSQL 스키마
CREATE TABLE adrg_kpis (
    id INTEGER PRIMARY KEY,
    hospital VARCHAR(10),
    period VARCHAR(20),
    adrg_code VARCHAR(10),
    adrg_name VARCHAR(200),
    patient_count INTEGER,
    target_los FLOAT,
    current_los FLOAT,
    los_gap FLOAT,
    additional_bed_days FLOAT
);
```

## ✅ 체크리스트

- [x] HIRA ADRG 테이블 파서 작성
- [x] ICD-10 자동 매핑 (282개)
- [x] 진단명 수동 매핑 변환 (132개)
- [x] SMC 데이터 ADRG 자동 매핑
- [x] ADRG 기반 집계 함수
- [x] ADRG 기반 KPI 계산
- [x] 전체 파이프라인 테스트
- [x] 정적 대시보드 재생성
- [x] 매칭률 50% 이상 달성 (58.1%)
- [x] 정합성 검증 통과
- [ ] 동적 대시보드 UI (선택)
- [ ] 데이터베이스 연동 (선택)
- [ ] 엑셀 다운로드 기능 (선택)

## 📞 문의

- 기술 문서: `CLAUDE.md`
- 실행 방법: `실행방법.md`
- 테스트: `python3 test_adrg_pipeline.py`
- GitHub Issues: [Report Issue](https://github.com/anthropics/claude-code/issues)

---

**작성자**: Claude Sonnet 4.5
**날짜**: 2026-02-23
**버전**: ADRG v1.0
