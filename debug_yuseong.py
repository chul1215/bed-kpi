import pandas as pd
import sys
sys.path.insert(0, 'backend')

from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator
from app.services.adrg_mapper import ADRGMapper
from app.services.period_classifier import PeriodClassifier
from app.config import settings

# HIRA 로드
hira_df = pd.read_excel('data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx', skiprows=2, header=0)
hira_df = hira_df[hira_df['4단DRG번호'] != '$'].copy()

# SMC 로드
smc_df = pd.read_excel('data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx', sheet_name='Sheet1')

# ADRG 매퍼 초기화 및 매핑
mapper = ADRGMapper()
mapper.hira_adrg_df = hira_df
mapper.load_icd10_to_adrg_mapping()
mapper.load_manual_diagnosis_mapping()
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

# 문제 진단: below_minimum과 no_target_los 상세 확인
below_min = adrg_kpi_df[adrg_kpi_df['status'] == 'below_minimum']
no_target = adrg_kpi_df[adrg_kpi_df['status'] == 'no_target_los']

print(f'❌ below_minimum (6명 미만): {len(below_min)}개')
print(f'❌ no_target_los: {len(no_target)}개')
print()

if len(no_target) > 0:
    print('no_target_los 상세 (환자수 많은 순 TOP 10):')
    no_target_sorted = no_target.sort_values('patient_count', ascending=False)
    for i, row in enumerate(no_target_sorted.head(10).itertuples(), 1):
        print(f"{i:2d}. {row.adrg_code:6s} | {row.patient_count:3d}명")
