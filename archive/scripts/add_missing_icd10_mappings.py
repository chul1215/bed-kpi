"""미매칭 ICD-10 코드를 KDRG 4.6에서 찾아서 추가"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('backend')))

import pandas as pd
from app.services.hospital_summary_parser import HospitalSummaryParser
from app.config import PROJECT_ROOT

# 1. 현재 매핑 파일 로드
print("1. 현재 ICD-10 매핑 로드...")
current_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx'
current_mapping_df = pd.read_excel(current_mapping_file)
current_icd10_codes = set(current_mapping_df['icd10_code'].tolist())
print(f"   현재 매핑: {len(current_icd10_codes)}개")

# 2. 병원 데이터에서 전체 ICD-10 코드 확인
print("\n2. 병원 데이터 ICD-10 코드 확인...")
hospital_summary_df = HospitalSummaryParser.parse_hospital_summary(
    PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
)
hospital_icd10_codes = hospital_summary_df['icd10_code'].dropna().unique()
print(f"   병원 ICD-10 코드: {len(hospital_icd10_codes)}개")

# 미매칭 코드
missing_codes = [code for code in hospital_icd10_codes if code not in current_icd10_codes]
print(f"   미매칭 코드: {len(missing_codes)}개")

# 3. KDRG 4.6 전체코드에서 미매칭 코드 찾기
print("\n3. KDRG 4.6 전체코드에서 미매칭 코드 검색...")
kdrg46_file = PROJECT_ROOT / 'data' / 'KDRG v4.6 전체코드.xlsx'
kdrg_icd_adrg_df = pd.read_excel(kdrg46_file, sheet_name='진단코드_ADRG매핑')

print(f"   KDRG 4.6 전체 매핑: {len(kdrg_icd_adrg_df):,}개")

# 새로 추가할 매핑
new_mappings = []

for icd10 in missing_codes:
    # KDRG 4.6에서 해당 코드로 시작하는 매핑 찾기
    matches = kdrg_icd_adrg_df[
        kdrg_icd_adrg_df['진단코드'].str.startswith(str(icd10), na=False)
    ]

    if len(matches) > 0:
        # 가장 많이 나타나는 ADRG 선택
        adrg_counts = matches['ADRG'].value_counts()
        most_common_adrg = adrg_counts.index[0]

        # 병원 데이터에서 해당 ICD-10 환자수 확인
        patient_count = hospital_summary_df[
            hospital_summary_df['icd10_code'] == icd10
        ]['patient_count'].sum()

        # 진단명
        diagnosis_names = hospital_summary_df[
            hospital_summary_df['icd10_code'] == icd10
        ]['diagnosis'].unique()
        diagnosis = diagnosis_names[0] if len(diagnosis_names) > 0 else ''

        new_mappings.append({
            'icd10_code': icd10,
            'adrg_code': most_common_adrg,
            'patient_count': patient_count,
            'diagnosis': diagnosis,
            'kdrg_match_count': len(matches)
        })

# 4. 결과 출력
print(f"\n✅ 새로 추가 가능한 매핑: {len(new_mappings)}개")
print("\n상위 20개 (환자수 기준):")
new_mappings_df = pd.DataFrame(new_mappings).sort_values('patient_count', ascending=False)

for idx, row in new_mappings_df.head(20).iterrows():
    print(f"  {row['patient_count']:3d}명 | {row['icd10_code']:6s} → {row['adrg_code']:6s} | {row['diagnosis'][:40]:40s} | KDRG 매치: {row['kdrg_match_count']}개")

# 5. 기존 매핑에 추가
print("\n4. 기존 매핑 파일 업데이트...")

# 기존 매핑
updated_mapping_df = current_mapping_df[['icd10_code', 'adrg_code']].copy()

# 새 매핑 추가
for mapping in new_mappings:
    updated_mapping_df = pd.concat([
        updated_mapping_df,
        pd.DataFrame([{
            'icd10_code': mapping['icd10_code'],
            'adrg_code': mapping['adrg_code']
        }])
    ], ignore_index=True)

# 중복 제거
updated_mapping_df = updated_mapping_df.drop_duplicates(subset=['icd10_code'])

# 저장
updated_mapping_df.to_excel(current_mapping_file, index=False)

print(f"\n✅ 업데이트 완료!")
print(f"   이전: {len(current_mapping_df)}개")
print(f"   현재: {len(updated_mapping_df)}개")
print(f"   추가: {len(new_mappings)}개")

# 6. 통계
total_hospital_codes = len(hospital_icd10_codes)
total_mapped = len(updated_mapping_df)
coverage = (total_mapped / total_hospital_codes * 100) if total_hospital_codes > 0 else 0

print(f"\n최종 커버리지: {total_mapped}/{total_hospital_codes} ({coverage:.1f}%)")
