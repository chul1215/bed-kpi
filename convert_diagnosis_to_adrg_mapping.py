"""
기존 진단명 → DRG 매핑을 진단명 → ADRG 매핑으로 변환
"""
import pandas as pd
from pathlib import Path

# 파일 경로
project_root = Path(__file__).parent
old_mapping_file = project_root / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'
hira_file = project_root / 'data' / 'hira' / '2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'
new_mapping_file = project_root / 'data' / 'mapping' / 'diagnosis_adrg_mapping.xlsx'

print("=" * 80)
print("진단명 → ADRG 매핑 변환")
print("=" * 80)

# 1. HIRA ADRG 테이블 로드
print("\n[1] HIRA ADRG 테이블 로드")
hira_df = pd.read_excel(hira_file, skiprows=2, header=0)
hira_df = hira_df[hira_df['4단DRG번호'] != '$'].copy()
hira_df = hira_df.dropna(subset=['4단DRG번호', 'ADRG명', '평균재원일수'])

# ADRG명 → ADRG 코드 매핑
adrg_name_to_code = dict(zip(hira_df['ADRG명'], hira_df['4단DRG번호']))
print(f"✅ HIRA ADRG: {len(adrg_name_to_code)}개")

# 2. 기존 진단명 → ADRG명 매핑 로드
print("\n[2] 기존 진단명 → ADRG명 매핑 로드")
old_mapping_df = pd.read_excel(old_mapping_file)
old_mapping_df = old_mapping_df.dropna(subset=['diagnosis', 'adrg_name'])
print(f"✅ 기존 매핑: {len(old_mapping_df)}개")

# 3. 진단명 → ADRG 코드 매핑 생성
print("\n[3] 진단명 → ADRG 코드 매핑 생성")
new_mappings = []
unmatched = []

for _, row in old_mapping_df.iterrows():
    diagnosis = row['diagnosis']
    adrg_name = row['adrg_name']

    # ADRG명으로 코드 조회
    adrg_code = adrg_name_to_code.get(adrg_name)

    if adrg_code:
        new_mappings.append({
            'diagnosis': diagnosis,
            'adrg_code': adrg_code,
            'adrg_name': adrg_name
        })
    else:
        unmatched.append({
            'diagnosis': diagnosis,
            'adrg_name': adrg_name,
            'note': 'ADRG명이 HIRA 테이블에 없음'
        })

new_mapping_df = pd.DataFrame(new_mappings)
print(f"✅ 변환 완료: {len(new_mapping_df)}개")
print(f"⚠️  미매칭: {len(unmatched)}개")

# 4. 엑셀 파일 저장
print("\n[4] 엑셀 파일 저장")
with pd.ExcelWriter(new_mapping_file) as writer:
    new_mapping_df.to_excel(writer, sheet_name='매핑', index=False)

    if unmatched:
        unmatched_df = pd.DataFrame(unmatched)
        unmatched_df.to_excel(writer, sheet_name='미매칭', index=False)

print(f"✅ 저장 완료: {new_mapping_file}")

# 5. 샘플 출력
print("\n[5] 샘플 매핑 (상위 10개)")
print(new_mapping_df.head(10).to_string(index=False))

print("\n" + "=" * 80)
print("✅ 변환 완료!")
print("=" * 80)
