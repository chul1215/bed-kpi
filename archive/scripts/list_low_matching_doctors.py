"""80% 미만 매칭률 의료진 리스트업"""
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
print("데이터 로드 중...")
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
matcher = KDRGMatcher()
matcher.load_kdrg_table(settings.PRELOADED_KDRG_FILE)
matcher.load_icd10_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx')
matcher.load_manual_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx')

# 매칭
smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_df, hira_df)

# 기간 분류
smc_matched = PeriodClassifier.add_period_column(smc_matched, 'discharge_date')

print("\n" + "="*100)
print("80% 미만 매칭률 의료진 리스트 (환자 10명 이상)")
print("="*100)

# 병원별, 기간별로 분석
for hospital in ['대전', '유성']:
    for period in ['off_season', 'normal']:
        period_name = '비수기' if period == 'off_season' else '통상기간'

        data = smc_matched[
            (smc_matched['hospital'] == hospital) &
            (smc_matched['period'] == period)
        ]

        # 의료진별 통계
        low_matching_doctors = []

        for doctor in data['doctor'].unique():
            doctor_data = data[data['doctor'] == doctor]
            total_patients = len(doctor_data)

            # 환자 10명 미만은 제외
            if total_patients < 10:
                continue

            matched_patients = doctor_data['target_los'].notna().sum()
            coverage = (matched_patients / total_patients * 100) if total_patients > 0 else 0

            # 80% 미만만 추출
            if coverage < 80.0:
                # 주요 미매칭 진단명 (상위 3개)
                unmatched_data = doctor_data[doctor_data['target_los'].isna()]
                top_unmatched = unmatched_data['diagnosis'].value_counts().head(3)

                unmatched_list = []
                for diagnosis, count in top_unmatched.items():
                    icd10 = diagnosis_to_icd10.get(diagnosis, 'N/A')
                    unmatched_list.append(f"{diagnosis}({count}명, {icd10})")

                low_matching_doctors.append({
                    'doctor': doctor,
                    'total_patients': total_patients,
                    'matched_patients': matched_patients,
                    'coverage': coverage,
                    'unmatched_diagnoses': ' | '.join(unmatched_list)
                })

        # 커버리지 낮은 순으로 정렬
        low_matching_doctors.sort(key=lambda x: x['coverage'])

        if len(low_matching_doctors) > 0:
            print(f"\n{'='*100}")
            print(f"{hospital}선병원 - {period_name}")
            print(f"{'='*100}")
            print(f"80% 미만 의료진: {len(low_matching_doctors)}명\n")

            for idx, doctor_info in enumerate(low_matching_doctors, 1):
                print(f"{idx}. {doctor_info['doctor']}")
                print(f"   환자: {doctor_info['total_patients']}명, 매칭: {doctor_info['matched_patients']}명 ({doctor_info['coverage']:.1f}%)")
                print(f"   주요 미매칭 진단: {doctor_info['unmatched_diagnoses']}")
                print()
        else:
            print(f"\n{'='*100}")
            print(f"{hospital}선병원 - {period_name}")
            print(f"{'='*100}")
            print(f"✅ 80% 미만 의료진 없음 (전원 80% 이상 달성)\n")

# 전체 요약
print("\n" + "="*100)
print("전체 요약")
print("="*100)

summary = []
for hospital in ['대전', '유성']:
    for period in ['off_season', 'normal']:
        period_name = '비수기' if period == 'off_season' else '통상기간'

        data = smc_matched[
            (smc_matched['hospital'] == hospital) &
            (smc_matched['period'] == period)
        ]

        low_count = 0
        total_count = 0

        for doctor in data['doctor'].unique():
            doctor_data = data[data['doctor'] == doctor]
            total_patients = len(doctor_data)

            if total_patients < 10:
                continue

            total_count += 1
            matched_patients = doctor_data['target_los'].notna().sum()
            coverage = (matched_patients / total_patients * 100) if total_patients > 0 else 0

            if coverage < 80.0:
                low_count += 1

        summary.append({
            'hospital': hospital,
            'period': period_name,
            'low_count': low_count,
            'total_count': total_count,
            'percentage': (low_count / total_count * 100) if total_count > 0 else 0
        })

print()
for item in summary:
    status = "✅" if item['low_count'] == 0 else "⚠️"
    print(f"{status} {item['hospital']} {item['period']:6s}: {item['low_count']:2d}명 / {item['total_count']:2d}명 ({item['percentage']:.1f}%)")
