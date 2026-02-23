"""전체 의료진 매칭률 분석"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('backend')))

from app.services.file_parser import FileParser
from app.services.kdrg_matcher import KDRGMatcher
from app.services.hospital_summary_parser import HospitalSummaryParser
from app.services.period_classifier import PeriodClassifier
from app.config import settings, PROJECT_ROOT
import pandas as pd

# 파일 로드
print("1. 데이터 로드 중...")
hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
smc_df = FileParser.parse_smc_file(settings.PRELOADED_SMC_FILE, filter_quarter=4)

# ICD-10 매핑
hospital_summary_df = HospitalSummaryParser.parse_hospital_summary(
    PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
)
diagnosis_to_icd10 = dict(zip(
    hospital_summary_df['diagnosis'],
    hospital_summary_df['icd10_code']
))
smc_df['icd10_code'] = smc_df['diagnosis'].map(diagnosis_to_icd10)

# KDRG Matcher
print("2. KDRG Matcher 초기화...")
matcher = KDRGMatcher()
matcher.load_kdrg_table(settings.PRELOADED_KDRG_FILE)
matcher.load_icd10_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx')
matcher.load_manual_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx')

# 매칭
smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_df, hira_df)

# 기간 분류
smc_matched = PeriodClassifier.add_period_column(smc_matched, 'discharge_date')

# 의료진별 매칭률 분석
print("\n3. 의료진별 매칭률 분석...")

results = []

for hospital in ['대전', '유성']:
    for period in ['off_season', 'normal']:
        period_name = '비수기' if period == 'off_season' else '통상기간'

        data = smc_matched[
            (smc_matched['hospital'] == hospital) &
            (smc_matched['period'] == period)
        ]

        # 의료진별 통계
        for doctor in data['doctor'].unique():
            doctor_data = data[data['doctor'] == doctor]
            total_patients = len(doctor_data)
            matched_patients = doctor_data['target_los'].notna().sum()
            coverage = (matched_patients / total_patients * 100) if total_patients > 0 else 0

            # 주요 진단명 (상위 3개)
            top_diagnoses = doctor_data['diagnosis'].value_counts().head(3)
            top_diagnosis_list = []
            for diagnosis, count in top_diagnoses.items():
                icd10 = diagnosis_to_icd10.get(diagnosis, 'N/A')
                has_target = diagnosis in disease_target_map
                status = '✅' if has_target else '❌'
                top_diagnosis_list.append(f"{status}{diagnosis}({count})")

            results.append({
                'hospital': hospital,
                'period': period_name,
                'doctor': doctor,
                'total_patients': total_patients,
                'matched_patients': matched_patients,
                'coverage': coverage,
                'top_diagnoses': ' | '.join(top_diagnosis_list)
            })

# DataFrame 생성
results_df = pd.DataFrame(results)

# 커버리지 낮은 순으로 정렬
results_df = results_df.sort_values('coverage')

print("\n" + "="*120)
print("매칭률 낮은 의료진 TOP 30 (전체 병원/기간)")
print("="*120)

low_coverage_df = results_df[results_df['total_patients'] >= 10].head(30)

for idx, row in low_coverage_df.iterrows():
    print(f"\n{row['hospital']} {row['period']} | {row['doctor']}")
    print(f"  환자: {row['total_patients']}명, 매칭: {row['matched_patients']}명 ({row['coverage']:.1f}%)")
    print(f"  주요 진단: {row['top_diagnoses']}")

# 통계 요약
print("\n" + "="*120)
print("전체 통계")
print("="*120)

for hospital in ['대전', '유성']:
    for period in ['비수기', '통상기간']:
        subset = results_df[
            (results_df['hospital'] == hospital) &
            (results_df['period'] == period) &
            (results_df['total_patients'] >= 10)
        ]

        if len(subset) > 0:
            avg_coverage = subset['coverage'].mean()
            low_count = len(subset[subset['coverage'] < 80])

            print(f"\n{hospital} {period}:")
            print(f"  평균 매칭률: {avg_coverage:.1f}%")
            print(f"  80% 미만 의료진: {low_count}명 / {len(subset)}명")

# 미매칭 진단명 분석
print("\n" + "="*120)
print("미매칭 진단명 TOP 20 (환자수 기준)")
print("="*120)

unmatched_diagnoses = smc_matched[smc_matched['target_los'].isna()]
unmatched_summary = unmatched_diagnoses.groupby('diagnosis').agg({
    'diagnosis': 'count'
}).rename(columns={'diagnosis': 'patient_count'})
unmatched_summary = unmatched_summary.sort_values('patient_count', ascending=False).head(20)

for diagnosis, row in unmatched_summary.iterrows():
    icd10 = diagnosis_to_icd10.get(diagnosis, 'N/A')
    print(f"  {row['patient_count']:3d}명 | {diagnosis:50s} | ICD-10: {str(icd10):6s}")

print("\n분석 완료!")
