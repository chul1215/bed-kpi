"""
HIRA 변환 후 유성 비수기 KPI 계산 문제 분석
"""
import pandas as pd
import sys
sys.path.insert(0, 'backend')

from app.services.file_parser import FileParser
from app.services.adrg_mapper import ADRGMapper
from app.config import settings

# 1. HIRA 로드
print("=" * 80)
print("HIRA 변환 후 유성 비수기 KPI 문제 분석")
print("=" * 80)
print()

hira_file = 'data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'
mapper = ADRGMapper()
hira_df = mapper.load_hira_adrg_table(hira_file)

# 2. 매핑 파일 로드
mapper.load_icd10_to_adrg_mapping('data/mapping/icd10_to_adrg_from_kdrg46.xlsx')
mapper.load_manual_diagnosis_mapping('data/mapping/diagnosis_adrg_mapping.xlsx')

# 3. SMC 로드 및 ADRG 매핑
smc_file = settings.PRELOADED_SMC_FILE
smc_df = FileParser.parse_smc_file(smc_file, filter_quarter=4, adrg_mapper=mapper)

# 4. 유성 비수기 필터
from app.services.period_classifier import PeriodClassifier
classifier = PeriodClassifier()
smc_df['period'] = smc_df['discharge_date'].apply(classifier.classify_period)

yuseong_off = smc_df[
    (smc_df['hospital'] == '유성') &
    (smc_df['period'] == 'off_season')
].copy()

print(f"유성 비수기 환자수: {len(yuseong_off)}명")
print()

# 5. ADRG 매칭 상태 확인
matched = yuseong_off[yuseong_off['adrg_code'].notna()]
print(f"ADRG 매칭: {len(matched)}/{len(yuseong_off)}명 ({len(matched)/len(yuseong_off)*100:.1f}%)")
print()

# 6. 진단명별 집계
from app.services.aggregator import Aggregator
adrg_agg = Aggregator.aggregate_by_adrg(matched)
print(f"집계된 ADRG: {len(adrg_agg)}개")
print()

# 7. KPI 계산
from app.services.kpi_calculator import KPICalculator
adrg_kpis = []
for _, row in adrg_agg.iterrows():
    kpi = KPICalculator.calculate_adrg_kpi(row)
    adrg_kpis.append(kpi)

adrg_kpi_df = pd.DataFrame(adrg_kpis)

# 8. Status별 분류
print("Status별 ADRG:")
for status in ['calculated', 'below_minimum', 'no_target_los']:
    count = len(adrg_kpi_df[adrg_kpi_df['status'] == status])
    if count > 0:
        print(f"  {status}: {count}개")
print()

# 9. calculated만 필터
valid = adrg_kpi_df[adrg_kpi_df['status'] == 'calculated'].copy()
print(f"✅ Status=calculated: {len(valid)}개")
print()

# 10. 추가 재원일수 계산
total = valid['additional_bed_days'].sum()
print(f"📊 총 추가 재원일수 (대시보드 표시): {total:+,.0f}일")
print()

# 11. 주요 진단명 분석 (환자수 많은 TOP 20)
print("=" * 120)
print("주요 ADRG 분석 (환자수 많은 순 TOP 20)")
print("=" * 120)
print(f"{'순위':>4} {'ADRG명':30} {'환자수':>6} {'목표LOS':>8} {'현재LOS':>8} {'갭':>8} {'추가재원일수':>12}")
print("-" * 120)

top20 = valid.sort_values('patient_count', ascending=False).head(20)
for i, row in enumerate(top20.itertuples(), 1):
    print(f"{i:4d} {row.adrg_name[:30]:30s} "
          f"{row.patient_count:6d}명 "
          f"{row.target_los:7.2f}일 "
          f"{row.current_los:7.2f}일 "
          f"{row.los_gap:+7.2f}일 "
          f"{row.additional_bed_days:+11,.0f}일")
print()

# 12. 양수/음수 기여도 분석
positive = valid[valid['additional_bed_days'] > 0]
negative = valid[valid['additional_bed_days'] < 0]

print("=" * 80)
print("추가 재원일수 기여도 분석")
print("=" * 80)
print(f"양수 (늘려야 함): {len(positive):3d}개 ADRG → +{positive['additional_bed_days'].sum():,.0f}일")
print(f"음수 (줄여야 함): {len(negative):3d}개 ADRG → {negative['additional_bed_days'].sum():,.0f}일")
print(f"{'─' * 80}")
print(f"순 합계:           {len(valid):3d}개 ADRG → {total:+,.0f}일 ⚠️")
print()

# 13. 문제 진단명 상세 (음수 기여도 TOP 10)
print("=" * 120)
print("⚠️  문제 ADRG (음수 기여도 TOP 10) - HIRA 목표 LOS가 너무 짧음")
print("=" * 120)
print(f"{'순위':>4} {'ADRG명':30} {'환자수':>6} {'목표LOS':>8} {'현재LOS':>8} {'갭':>8} {'추가재원일수':>12}")
print("-" * 120)

negative_top10 = negative.sort_values('additional_bed_days').head(10)
for i, row in enumerate(negative_top10.itertuples(), 1):
    print(f"{i:4d} {row.adrg_name[:30]:30s} "
          f"{row.patient_count:6d}명 "
          f"{row.target_los:7.2f}일 "
          f"{row.current_los:7.2f}일 "
          f"{row.los_gap:+7.2f}일 "
          f"{row.additional_bed_days:+11,.0f}일 ⚠️")
print()

print("💡 결론:")
print(f"   - 음수 ADRG들의 HIRA 목표 LOS가 1~3일로 매우 짧음")
print(f"   - 실제 현재 LOS는 3~15일 수준")
print(f"   - KDRG → HIRA 변환이 부적절하거나, HIRA 테이블 자체의 한계")
print(f"   - **KDRG 4.6 공식 목표 LOS 테이블 확보 필요** ⭐")
print()
