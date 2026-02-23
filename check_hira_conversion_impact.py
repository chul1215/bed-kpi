import pandas as pd
import sys
sys.path.insert(0, 'backend')

from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator
from app.services.adrg_mapper import ADRGMapper
from app.services.period_classifier import PeriodClassifier

# HIRA 로드
hira_df = pd.read_excel('data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx', skiprows=2, header=0)
hira_df = hira_df[hira_df['4단DRG번호'] != '$'].copy()

# SMC 로드
smc_df = pd.read_excel('data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx', sheet_name='Sheet1')

# ADRG 매퍼 초기화 및 매핑
mapper = ADRGMapper()
mapper.hira_adrg_df = hira_df
mapper.load_icd10_to_adrg_mapping('data/mapping/icd10_to_adrg_from_kdrg46.xlsx')
mapper.load_manual_diagnosis_mapping('data/mapping/diagnosis_adrg_mapping.xlsx')
smc_df = mapper.add_adrg_to_smc(smc_df)

# 기간 분류
classifier = PeriodClassifier()
smc_df['period'] = smc_df['discharge_date'].apply(classifier.classify_period)

# 유성 비수기만 필터
period_df = smc_df[
    (smc_df['hospital'] == '유성') &
    (smc_df['period'] == 'off_season')
].copy()

print(f'유성 비수기: {len(period_df)}명')
print()

# ADRG 집계
adrg_agg = Aggregator.aggregate_by_adrg(period_df)
print(f'집계된 ADRG: {len(adrg_agg)}개')
print()

# ADRG KPI 계산
adrg_kpis = []
for _, row in adrg_agg.iterrows():
    kpi = KPICalculator.calculate_adrg_kpi(row)
    adrg_kpis.append(kpi)

adrg_kpi_df = pd.DataFrame(adrg_kpis)

# Status별 개수
print('Status별 ADRG:')
for status, count in adrg_kpi_df['status'].value_counts().items():
    print(f'  {status}: {count}개')
print()

# calculated만 필터
valid_adrg_kpis = adrg_kpi_df[adrg_kpi_df['status'] == 'calculated']
print(f'✅ Status=calculated: {len(valid_adrg_kpis)}개')
print()

# 추가 재원일수
total_additional_bed_days = valid_adrg_kpis['additional_bed_days'].sum()
print(f'📊 총 추가 재원일수 (calculated만): {total_additional_bed_days:+,.0f}일')
print()

# 문제 진단: 주요 진단명들의 LOS 갭 확인
print('주요 진단명 LOS 갭 분석 (환자수 많은 순 TOP 10):')
print()

# calculated 중 환자수 많은 순
top_diagnoses = valid_adrg_kpis.sort_values('patient_count', ascending=False).head(10)

for i, row in enumerate(top_diagnoses.itertuples(), 1):
    gap_sign = "+" if row.los_gap > 0 else ""
    print(f"{i:2d}. {row.adrg_name[:30]:30s} | "
          f"{row.patient_count:3d}명 | "
          f"목표 {row.target_los:5.2f}일 | "
          f"현재 {row.current_los:5.2f}일 | "
          f"갭 {gap_sign}{row.los_gap:+5.2f}일 | "
          f"추가 {row.additional_bed_days:+7,.0f}일")
print()

# 양수/음수 기여도 분석
positive = valid_adrg_kpis[valid_adrg_kpis['additional_bed_days'] > 0]
negative = valid_adrg_kpis[valid_adrg_kpis['additional_bed_days'] < 0]

print(f'양수 기여 (늘려야 함): {len(positive)}개 진단명 → +{positive["additional_bed_days"].sum():,.0f}일')
print(f'음수 기여 (줄여야 함): {len(negative)}개 진단명 → {negative["additional_bed_days"].sum():,.0f}일')
print(f'순 합계: {total_additional_bed_days:+,.0f}일')
