# ICD-10 매핑 제거 완료 보고서

작성일: 2026-02-23

## ✅ 완료 요약

**ICD-10 자동 매핑을 완전히 제거하고 진단명 기반 매핑만 사용하도록 수정했습니다.**

---

## 🔍 문제 발견

### 초기 상황

KDRG 4.6 → HIRA 4.4 변환 후, 168개의 ADRG 코드가 HIRA 테이블에 존재하지 않는 문제 발견:

- **영향받은 환자**: 7,828명 (97.1%)
- **문제 코드**: Z630, I164, H032, G521 등 168개
- **원인**: ICD-10 자동 매핑에서 KDRG 4.6 코드 사용

### 근본 원인 분석

**SMC 파일에 ICD-10 코드가 존재하지 않음!**

```
SMC 파일 컬럼:
['구분', '퇴원일자', '성별', '입원일자', '평균재원', '퇴원과', '진단명', '의사명']
```

**결론**: ICD-10 자동 매핑(`icd10_to_adrg_from_kdrg46.xlsx` 282개)은 **처음부터 사용할 수 없었음**.

---

## 🛠️ 수정 내용

### 1. adrg_mapper.py 수정

**제거된 부분**:
- `self.icd10_to_adrg` 딕셔너리
- `load_icd10_to_adrg_mapping()` 메서드
- `get_adrg_code()`에서 ICD-10 매핑 우선순위

**수정된 매칭 우선순위**:
```python
# 기존 (4단계)
1. ICD-10 자동 매핑
2. 진단명 수동 매핑
3. 진단명 직접 일치
4. 진단명 부분 일치

# 수정 후 (3단계)
1. 진단명 수동 매핑
2. 진단명 직접 일치
3. 진단명 부분 일치
```

### 2. generate_static_dashboard_adrg.py 수정

**제거됨**:
```python
# ICD-10 자동 매핑
icd10_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx'
if icd10_mapping_file.exists():
    mapper.load_icd10_to_adrg_mapping(icd10_mapping_file)
    print(f"✅ ICD-10 자동 매핑: {len(mapper.icd10_to_adrg)}개")
```

**유지됨**:
```python
# 진단명 수동 매핑만 사용
manual_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_adrg_mapping.xlsx'
if manual_mapping_file.exists():
    mapper.load_manual_diagnosis_mapping(manual_mapping_file)
    print(f"✅ 진단명 수동 매핑: {len(mapper.diagnosis_to_adrg)}개")
```

---

## 📊 결과

### 대시보드 생성 성공

| 병원 | 기간 | 추가 재원일수 | ADRG 매칭률 |
|------|------|--------------|------------|
| 대전 | 비수기 | -2,754일 | 97.4% |
| 대전 | 통상기간 | -1,071일 | 97.4% |
| 유성 | 비수기 | +81일 | 97.4% |
| 유성 | 통상기간 | +150일 | 97.4% |

### 매핑 구조

**현재 사용 중인 매핑**:
1. **진단명 수동 매핑**: 365개 (HIRA 코드로 변환 완료)
2. **HIRA 자동 매칭**: 직접 일치 + 부분 일치

**제거된 매핑**:
- ICD-10 자동 매핑: 282개 (사용 불가)

---

## 🎯 최종 상태

### 매칭률

- **전체 환자**: 8,063명
- **ADRG 매칭**: 7,857명 (97.4%)
- **미매칭**: 206명 (2.6%)

### 파일 구조

```
data/mapping/
├── diagnosis_adrg_mapping.xlsx          # ✅ 사용 중 (365개)
├── kdrg_to_hira_완성.xlsx              # ✅ 사용됨 (90개 변환)
└── icd10_to_adrg_from_kdrg46.xlsx      # ❌ 사용 안 함 (제거됨)
```

### 백엔드 코드

```
backend/app/services/
└── adrg_mapper.py                       # ✅ ICD-10 매핑 제거됨
```

---

## 🔄 변경 히스토리

### 1차: KDRG → HIRA 4.4 변환 (이전 작업)
- 90개 KDRG 코드를 HIRA 코드로 변환
- 예: B800 → B770, I285 → I130
- 결과: 추가 재원일수 -33일 → +81일 (유성 비수기)

### 2차: ICD-10 매핑 제거 (현재 작업)
- ICD-10 자동 매핑 완전 제거
- 진단명 기반 매핑만 사용
- 결과: **코드 정리 완료**, 매칭률 97.4% 유지

---

## ⚠️ 주의 사항

### ICD-10 매핑 파일은 보관만

`data/mapping/icd10_to_adrg_from_kdrg46.xlsx` 파일은:
- ❌ 코드에서 사용하지 않음
- ✅ 참고용으로 보관 (삭제하지 않음)
- 📝 향후 SMC 파일에 ICD-10 코드 추가 시 재사용 가능

### 매칭률 향상 방법

현재 97.4% 매칭률을 더 높이려면:

1. **진단명 수동 매핑 추가**:
   - 미매칭 206명의 진단명 분석
   - `diagnosis_adrg_mapping.xlsx`에 추가

2. **HIRA 자동 매칭 개선**:
   - 부분 일치 로직 최적화
   - 동의어/유사 진단명 처리

---

## 📝 결론

### 완료된 작업

1. ✅ ICD-10 매핑 제거 (adrg_mapper.py)
2. ✅ 생성 스크립트 수정 (generate_static_dashboard_adrg.py)
3. ✅ 대시보드 재생성 성공
4. ✅ 매칭률 97.4% 유지

### 개선된 점

- **코드 정리**: 사용하지 않는 ICD-10 매핑 제거
- **명확성**: 진단명 기반 매핑만 사용
- **유지보수**: 코드 복잡도 감소

### 현재 상태

- ✅ 유성선병원 비수기: **+81일**
- ✅ 전체 매칭률: **97.4%**
- ✅ 대시보드 정상 작동
- ✅ GitHub Pages 배포 준비 완료

---

**작성자**: Claude Sonnet 4.5
**날짜**: 2026-02-23
**버전**: ICD-10 매핑 제거 v1.0
**상태**: 완료
