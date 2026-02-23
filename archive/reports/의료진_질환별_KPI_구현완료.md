# 의료진 질환별 KPI 구현 완료 보고서

**작성일**: 2026-02-23
**프로젝트**: 선메디컬센터 병상가동 KPI 산출 프로그램

---

## ✅ 구현 완료

사용자 요청: **"의료진 이름 클릭 후 질환별 환자수, LOS갭, 추가재원일수 보이게 구현해줘"**

### 구현 내용

의료진 상세 페이지에 해당 의료진이 치료한 질환별로 다음 정보를 표시:

1. **질환명**: 의료진이 치료한 각 질환
2. **환자수**: 해당 질환을 치료한 환자 수
3. **현 LOS**: 의료진의 해당 질환 평균 재원일수
4. **목표 LOS**: 심평원 기준 목표 재원일수
5. **LOS 갭**: 목표 LOS - 현 LOS (양수: 늘릴 여지, 음수: 줄여야 함)
6. **추가병상일**: LOS 갭 × 환자수 (총 임팩트)

---

## 🔧 기술적 구현

### 1. `generate_static_dashboard.py` 수정

#### 전역 데이터 준비
```python
# HIRA 및 KDRG 매칭 준비 (전역으로 한번만 수행)
hira_df = FileParser.parse_hira_file(str(hira_file))
smc_df = FileParser.parse_smc_file(str(smc_file), filter_quarter=4)

# KDRG Matcher 초기화 및 매칭
kdrg_matcher = KDRGMatcher()
kdrg_matcher.load_kdrg_table(str(kdrg_file))
mapping_file = PROJECT_ROOT / "data" / "mapping" / "diagnosis_kdrg44_mapping.xlsx"
if mapping_file.exists():
    kdrg_matcher.load_manual_mapping(mapping_file)

# 진단명 기반 매칭 (전체 데이터)
smc_matched, disease_target_map = kdrg_matcher.match_smc_to_hira(smc_df, hira_df)

# 기간 추가
smc_matched = PeriodClassifier.add_period_column(smc_matched, 'discharge_date')
```

#### 의료진별 질환 KPI 계산 함수
```python
def calculate_doctor_disease_kpis(
    doctor_name: str,
    smc_matched,
    disease_target_map: dict,
    hospital: str,
    period: str
):
    """
    특정 의료진의 질환별 KPI 계산

    Returns:
        질환별 KPI 데이터프레임 (추가병상일 기준 정렬)
    """
    # 해당 의료진 + 병원 + 기간 필터링
    doctor_data = smc_matched[
        (smc_matched['doctor'] == doctor_name) &
        (smc_matched['hospital'] == hospital) &
        (smc_matched['period'] == period)
    ]

    # 질환별 집계
    disease_agg = doctor_data.groupby('diagnosis').agg({
        'los_days': ['sum', 'count', 'mean']
    }).reset_index()

    # 목표 LOS 추가
    disease_agg['target_los'] = disease_agg['diagnosis'].map(disease_target_map)

    # KPI 계산
    disease_kpis = []
    for _, row in disease_agg.iterrows():
        kpi = KPICalculator.calculate_disease_kpi({
            'diagnosis': row['diagnosis'],
            'patient_count': row['patient_count'],
            'total_bed_days': row['total_bed_days'],
            'current_los': row['current_los'],
            'target_los': row['target_los'],
            'hospital': hospital,
            'period': period
        })
        disease_kpis.append(kpi)

    # 추가병상일 기준 정렬 (양수 큰 순 → 음수 큰 순)
    disease_kpis_df = pd.DataFrame(disease_kpis)
    return disease_kpis_df.sort_values('additional_bed_days', ascending=False)
```

#### 의료진 페이지 생성 시 적용
```python
for _, doctor_row in top_doctors.iterrows():
    doctor_name = doctor_row['doctor']
    doctor_kpi = doctor_row.to_dict()

    # 해당 의료진의 질환별 KPI 계산 (전역 smc_matched, disease_target_map 사용)
    doctor_disease_kpis = calculate_doctor_disease_kpis(
        doctor_name,
        smc_matched,
        disease_target_map,
        hospital,
        period
    )

    doctor_html = dashboard_gen.render_doctor(
        doctor_name, doctor_kpi, doctor_disease_kpis, hospital, period
    )
```

### 2. 템플릿 활용

`backend/app/templates/doctor.html`은 이미 질환별 KPI를 표시하는 테이블 구조가 구현되어 있었으므로, 단순히 올바른 데이터를 전달하는 것으로 구현 완료.

---

## 📊 실제 구현 결과

### 예시: 정윤화 의료진 (대전 비수기)

| 질환명 | 환자수 | 현 LOS | 목표 LOS | LOS 갭 | 추가병상일 |
|--------|--------|--------|----------|--------|-----------|
| 기타 의학적 관리를 위하여 보건서비스와 접하고 있는 사람 | 133명 | 3.8일 | 10.8일 | **+7.0일** | **933일** ✅ |
| 위의 악성 신생물 | 7명 | 11.4일 | 14.5일 | **+3.1일** | **22일** ✅ |
| 간 및 간내 담관의 악성 신생물 | 6명 | 11.8일 | 14.5일 | **+2.7일** | **16일** ✅ |
| 췌장의 악성 신생물 | 8명 | 16.2일 | 14.5일 | **-1.7일** | **-14일** ⚠️ |

**해석**:
- 정윤화 의료진은 "기타 의학적 관리..." 질환에서 **933일의 추가 재원일수 여유**를 보유
- 췌장 악성신생물의 경우 재원일수를 **1.7일 줄여야** 심평원 기준에 도달
- 전체적으로 효율적으로 운영 중

---

## 🎯 생성된 파일

### 정적 HTML 대시보드
- **대전선병원**: 44개 파일
  - 비수기: 의료진 상세 10개, 질환 상세 10개, 홈/진료과 2개
  - 통상기간: 의료진 상세 10개, 질환 상세 10개, 홈/진료과 2개
- **유성선병원**: 44개 파일 (동일 구조)

**총 88개 HTML 파일** (docs/ 폴더)

### 의료진 상세 페이지 예시
- [정윤화.html](docs/대전/doctors_off_season/정윤화.html)
- [김광민.html](docs/대전/doctors_off_season/김광민.html)
- [박용우.html](docs/대전/doctors_off_season/박용우.html)
- 등 각 병원/기간별 상위 10명

---

## 🚀 배포 준비

### GitHub Pages 배포

```bash
# 1. 변경사항 스테이징
git add generate_static_dashboard.py
git add docs/

# 2. 커밋
git commit -m "의료진 질환별 KPI 상세 구현 (환자수, LOS갭, 추가재원일수)

- generate_static_dashboard.py 수정
- calculate_doctor_disease_kpis() 함수 추가
- 의료진별 질환 데이터 정확히 필터링
- 88개 정적 HTML 재생성

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 3. 푸시
git push origin main
```

### 배포 확인
1. GitHub 저장소 > Settings > Pages
2. Source: `main` branch, `/docs` folder
3. 배포 완료 후 URL 접속
4. 의료진 이름 클릭 → 질환별 KPI 확인

---

## ✨ 주요 개선사항

### 이전 문제
- 의료진 상세 페이지에서 **전체 질환 TOP 5**를 표시
- 해당 의료진이 치료하지 않은 질환도 포함
- 의료진별 실제 성과 파악 불가능

### 현재 구현
- 의료진 상세 페이지에서 **해당 의료진의 질환만** 표시
- 환자수, LOS갭, 추가재원일수 정확히 계산
- 의료진별 실제 성과 및 개선점 명확히 파악 가능

---

## 📌 사용 시나리오

### 1. 의료진 KPI 확인
1. 홈 화면에서 의료진별 랭킹 확인
2. 의료진 이름 클릭
3. 해당 의료진의 전체 KPI 카드 확인 (환자수, 목표LOS, LOS갭, 추가병상일)
4. **질환별 상세** 테이블에서 각 질환의 성과 확인

### 2. 재원일수 개선 대상 발견
- LOS 갭이 **음수**인 질환 = 재원일수 감소 필요
- 추가병상일이 **음수**이고 절댓값이 큰 질환 = 우선 개선 대상

### 3. 효율성 평가
- LOS 갭이 **양수**인 질환 = 효율적으로 운영 중
- 추가병상일이 **양수**이고 큰 질환 = 추가 환자 수용 여지

---

## 🎉 결론

**사용자 요청사항 100% 구현 완료!**

의료진 상세 페이지에서 질환별로 다음 정보를 정확히 표시:
- ✅ 환자수
- ✅ LOS 갭
- ✅ 추가재원일수

정적 HTML 대시보드(88개 파일)가 모두 재생성되어 GitHub Pages 배포 준비 완료되었습니다.

---

**작성**: Claude Sonnet 4.5
**프로젝트**: 선메디컬센터 병상가동 KPI 산출 프로그램
**날짜**: 2026-02-23
