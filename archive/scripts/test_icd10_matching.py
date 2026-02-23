"""ICD-10 기반 매칭 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.file_parser import FileParser
from app.services.kdrg_matcher import KDRGMatcher
from app.services.hospital_summary_parser import HospitalSummaryParser
from app.config import settings, PROJECT_ROOT

# 1. HIRA 파일 로드
print("1. HIRA 파일 로드...")
hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
print(f"   HIRA: {len(hira_df)}건")
print(f"   컬럼: {hira_df.columns.tolist()}")
print(f"   adrg_code 샘플: {hira_df['adrg_code'].head()}")

# 2. SMC 파일 로드
print("\n2. SMC 파일 로드 (4분기)...")
smc_df = FileParser.parse_smc_file(settings.PRELOADED_SMC_FILE, filter_quarter=4)
print(f"   SMC: {len(smc_df)}건")

# 3. 병원별 시트에서 ICD-10 코드 로드
print("\n3. 병원별 시트 ICD-10 코드 로드...")
hospital_summary_df = HospitalSummaryParser.parse_hospital_summary(
    PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
)
print(f"   병원별 시트: {len(hospital_summary_df)}건")

# 진단명 → ICD-10 코드 매핑
diagnosis_to_icd10 = dict(zip(
    hospital_summary_df['diagnosis'],
    hospital_summary_df['icd10_code']
))
smc_df['icd10_code'] = smc_df['diagnosis'].map(diagnosis_to_icd10)

icd10_coverage = smc_df['icd10_code'].notna().sum()
print(f"   ICD-10 커버리지: {icd10_coverage}/{len(smc_df)} ({icd10_coverage/len(smc_df)*100:.1f}%)")

# 4. KDRG Matcher 초기화
print("\n4. KDRG Matcher 초기화...")
matcher = KDRGMatcher()
matcher.load_kdrg_table(settings.PRELOADED_KDRG_FILE)

# ICD-10 매핑 로드
icd10_mapping_file = PROJECT_ROOT / "data" / "mapping" / "icd10_to_adrg_from_kdrg46.xlsx"
if icd10_mapping_file.exists():
    matcher.load_icd10_mapping(icd10_mapping_file)
    print(f"   ICD-10 매핑 로드: {len(matcher.icd10_to_adrg)}개")
else:
    print(f"   ⚠️  ICD-10 매핑 파일 없음!")

# 수동 매핑 로드
mapping_file = PROJECT_ROOT / "data" / "mapping" / "diagnosis_kdrg44_mapping.xlsx"
if mapping_file.exists():
    matcher.load_manual_mapping(mapping_file)
    print(f"   진단명 수동 매핑 로드: {len(matcher.diagnosis_to_adrg)}개")

# 5. 매칭 테스트
print("\n5. 매칭 테스트...")

# 대전 4분기만 테스트
smc_test = smc_df[smc_df['hospital'] == '대전'].copy()
print(f"   대전 4분기: {len(smc_test)}건")

smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_test, hira_df)

# 6. 결과 분석
print("\n6. 결과 분석...")
total_patients = len(smc_matched)
matched_patients = smc_matched['target_los'].notna().sum()
print(f"   매칭된 환자: {matched_patients}/{total_patients} ({matched_patients/total_patients*100:.1f}%)")

# ICD-10 코드별 매칭 성공/실패
matched_with_icd10 = smc_matched[
    (smc_matched['icd10_code'].notna()) &
    (smc_matched['target_los'].notna())
]
total_with_icd10 = smc_matched['icd10_code'].notna().sum()
print(f"   ICD-10 있는 레코드: {total_with_icd10}건")
print(f"   ICD-10 매칭 성공: {len(matched_with_icd10)}건 ({len(matched_with_icd10)/total_with_icd10*100:.1f}%)")

# 샘플 확인
print("\n7. 샘플 확인 (상위 5개)...")
for i, (diagnosis, target_los) in enumerate(list(disease_target_map.items())[:5]):
    icd10 = diagnosis_to_icd10.get(diagnosis, None)
    print(f"   {i+1}. {diagnosis} ({icd10}) → {target_los}")
