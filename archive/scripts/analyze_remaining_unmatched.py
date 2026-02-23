"""미매칭 진단명 상세 분석 - 100% 달성 방안"""
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
print("미매칭 진단명 상세 분석 - 100% 달성 방안")
print("="*100)

# 미매칭 데이터
unmatched = smc_matched[smc_matched['target_los'].isna()]

print(f"\n총 미매칭 환자: {len(unmatched)}명 / {len(smc_matched)}명 ({len(unmatched)/len(smc_matched)*100:.1f}%)")

# 1. 미매칭 진단명별 환자수 (상위 30개)
print("\n" + "="*100)
print("미매칭 진단명 TOP 30 (환자수 기준)")
print("="*100)

unmatched_summary = unmatched.groupby('diagnosis').agg({
    'diagnosis': 'count',
    'hospital': lambda x: ', '.join(x.unique()),
    'icd10_code': 'first'
}).rename(columns={'diagnosis': 'patient_count'})
unmatched_summary = unmatched_summary.sort_values('patient_count', ascending=False).head(30)

total_unmatched = 0
for idx, (diagnosis, row) in enumerate(unmatched_summary.iterrows(), 1):
    icd10 = row['icd10_code'] if pd.notna(row['icd10_code']) else 'N/A'
    hospitals = row['hospital']
    count = row['patient_count']
    total_unmatched += count

    print(f"{idx:2d}. [{count:3d}명] {diagnosis:50s} | ICD-10: {str(icd10):6s} | {hospitals}")

cumulative_coverage = (total_unmatched / len(unmatched)) * 100
print(f"\nTOP 30 커버리지: {total_unmatched}명 / {len(unmatched)}명 ({cumulative_coverage:.1f}%)")

# 2. ICD-10 코드 유무별 분류
print("\n" + "="*100)
print("미매칭 진단명 분류")
print("="*100)

unmatched_with_icd10 = unmatched[unmatched['icd10_code'].notna()]
unmatched_without_icd10 = unmatched[unmatched['icd10_code'].isna()]

print(f"\n1. ICD-10 코드 있음: {len(unmatched_with_icd10)}명 ({len(unmatched_with_icd10)/len(unmatched)*100:.1f}%)")
print(f"   → KDRG 4.6에 없거나 HIRA에 없는 코드")
print(f"   → 해결 방법: 유사 ADRG로 수동 매핑 추가")

print(f"\n2. ICD-10 코드 없음: {len(unmatched_without_icd10)}명 ({len(unmatched_without_icd10)/len(unmatched)*100:.1f}%)")
print(f"   → 병원 데이터에 ICD-10 코드 누락")
print(f"   → 해결 방법: 병원 측에 데이터 보완 요청 또는 진단명으로 수동 매핑")

# 3. ICD-10 있는 미매칭 진단명 (TOP 20)
if len(unmatched_with_icd10) > 0:
    print("\n" + "="*100)
    print("ICD-10 코드는 있지만 매칭 안 된 진단명 TOP 20")
    print("="*100)

    icd10_unmatched = unmatched_with_icd10.groupby(['diagnosis', 'icd10_code']).size().reset_index(name='count')
    icd10_unmatched = icd10_unmatched.sort_values('count', ascending=False).head(20)

    for idx, row in icd10_unmatched.iterrows():
        print(f"  {row['count']:3d}명 | {row['diagnosis']:50s} | ICD-10: {row['icd10_code']}")

# 4. ICD-10 없는 미매칭 진단명 (TOP 20)
if len(unmatched_without_icd10) > 0:
    print("\n" + "="*100)
    print("ICD-10 코드 없는 미매칭 진단명 TOP 20")
    print("="*100)

    no_icd10_unmatched = unmatched_without_icd10.groupby('diagnosis').size().reset_index(name='count')
    no_icd10_unmatched = no_icd10_unmatched.sort_values('count', ascending=False).head(20)

    for idx, row in no_icd10_unmatched.iterrows():
        print(f"  {row['count']:3d}명 | {row['diagnosis']}")

# 5. 개선 우선순위
print("\n" + "="*100)
print("100% 달성을 위한 개선 우선순위")
print("="*100)

# TOP 10 진단명 분석
top10_diagnoses = unmatched_summary.head(10).index.tolist()
top10_count = unmatched_summary.head(10)['patient_count'].sum()
top10_coverage = (top10_count / len(unmatched)) * 100

print(f"\n우선순위 1: TOP 10 진단명 매핑 추가")
print(f"  → 대상: {len(top10_diagnoses)}개 진단명")
print(f"  → 환자수: {top10_count}명")
print(f"  → 예상 개선: {top10_coverage:.1f}% (미매칭의 {top10_coverage:.1f}%)")
print(f"  → 소요 시간: 약 30분")

# ICD-10 코드 보완
icd10_missing_count = len(unmatched_without_icd10)
icd10_missing_coverage = (icd10_missing_count / len(unmatched)) * 100

print(f"\n우선순위 2: 병원 데이터 ICD-10 코드 보완")
print(f"  → 대상: ICD-10 코드 없는 진단명")
print(f"  → 환자수: {icd10_missing_count}명")
print(f"  → 예상 개선: {icd10_missing_coverage:.1f}%")
print(f"  → 소요 시간: 병원 측 협조 필요")

# 전체 매핑 확장
remaining = len(unmatched) - top10_count
remaining_coverage = (remaining / len(unmatched)) * 100

print(f"\n우선순위 3: 나머지 전체 진단명 매핑")
print(f"  → 대상: {len(unmatched_summary) - 10}개 진단명")
print(f"  → 환자수: {remaining}명")
print(f"  → 예상 개선: {remaining_coverage:.1f}%")
print(f"  → 소요 시간: 약 1-2시간")

print("\n" + "="*100)
print("결론")
print("="*100)
print(f"\n현재 매칭률: {(len(smc_matched) - len(unmatched))/len(smc_matched)*100:.1f}%")
print(f"100% 달성까지 필요한 매핑: {len(unmatched_summary)}개 진단명")
print(f"  - ICD-10 있음: 수동 매핑 추가 가능")
print(f"  - ICD-10 없음: 병원 데이터 보완 필요")
print(f"\nTOP 10만 매핑 시 예상 매칭률: {((len(smc_matched) - len(unmatched) + top10_count)/len(smc_matched)*100):.1f}%")
print(f"전체 매핑 시 예상 매칭률: 100%")
