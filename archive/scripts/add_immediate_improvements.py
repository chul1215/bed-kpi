"""즉시 개선 가능한 진단명 수동 매핑 추가"""
import sys
from pathlib import Path
sys.path.insert(0, 'backend')

import pandas as pd
from app.services.file_parser import FileParser
from app.config import settings, PROJECT_ROOT

# 1. 현재 매핑 로드
mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'
current_df = pd.read_excel(mapping_file)
print(f'현재 수동 매핑: {len(current_df)}개')

# 2. HIRA 로드
hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
hira_adrg_names = set(hira_df['adrg_name'].tolist())

# 3. 추가할 매핑 (즉시 개선 가능)
new_mappings = [
    # 이비인후과 (장희상, 신명석)
    {'diagnosis': '급성 편도염', 'adrg_name': '편도 및 아데노이드수술'},
    {'diagnosis': '침샘의 질환', 'adrg_name': '기타 안면골 절제술'},
    {'diagnosis': '달리 분류되지 않은 성대 및 후두의 질환', 'adrg_name': '후두절제술'},
    {'diagnosis': '만성 비염, 비인두염 및 인두염', 'adrg_name': '만성 부비동염'},
    {'diagnosis': '급성 후두염 및 기관염', 'adrg_name': '후두절제술'},

    # 신경과 (김병석)
    {'diagnosis': '달리 분류되지 않은 언어장애', 'adrg_name': '뇌신경 및 말초신경 손상'},
    {'diagnosis': '피부감각의 장애', 'adrg_name': '뇌신경 및 말초신경 손상'},

    # 소화기내과 (서의근)
    {'diagnosis': '항문 및 직장의 기타 질환', 'adrg_name': '항문 및 항문주위 수술'},
    {'diagnosis': '과민대장증후군', 'adrg_name': '장의 기타 질환'},
    {'diagnosis': '십이지장궤양', 'adrg_name': '위장관계통의 소화성궤양'},

    # 기타
    {'diagnosis': '이상불수의운동', 'adrg_name': '뇌신경 및 말초신경 손상'},
    {'diagnosis': '뇌손상, 뇌기능이상 및 신체질환에 의한 기타 정신장애', 'adrg_name': '기타 뇌혈관질환'},
    {'diagnosis': '중추신경계통의 기타 장애', 'adrg_name': '기타 뇌혈관질환'},
    {'diagnosis': '기타 추체외로 및 운동 장애', 'adrg_name': '뇌신경 및 말초신경 손상'},
    {'diagnosis': '뇌염, 척수염 및 뇌척수염', 'adrg_name': '뇌신경계통의 감염'},
]

print('\n=== 매핑 검증 ===')
valid_mappings = []

for mapping in new_mappings:
    diagnosis = mapping['diagnosis']
    adrg_name = mapping['adrg_name']

    # 이미 있는지 확인
    if diagnosis in current_df['diagnosis'].values:
        print(f'⏭️  {diagnosis:50s} → 이미 존재')
        continue

    # HIRA에 ADRG명이 있는지 확인
    if adrg_name in hira_adrg_names:
        valid_mappings.append(mapping)
        target_los = hira_df[hira_df['adrg_name'] == adrg_name].iloc[0]['target_los']
        print(f'✅ {diagnosis:50s} → {adrg_name} (LOS: {target_los:.2f})')
    else:
        # 유사한 ADRG 찾기
        similar = [name for name in hira_adrg_names if adrg_name.split()[0] in name]
        if similar:
            print(f'⚠️  {diagnosis:50s} → ADRG명 정확히 없음. 유사: {similar[0]}')
        else:
            print(f'❌ {diagnosis:50s} → ADRG명 없음: {adrg_name}')

print(f'\n추가 가능: {len(valid_mappings)}개')

# 4. 매핑 추가
if len(valid_mappings) > 0:
    new_rows_df = pd.DataFrame(valid_mappings)
    updated_df = pd.concat([current_df, new_rows_df], ignore_index=True)

    # 저장
    updated_df.to_excel(mapping_file, index=False)

    print(f'\n✅ 매핑 파일 업데이트 완료!')
    print(f'   이전: {len(current_df)}개')
    print(f'   현재: {len(updated_df)}개')
    print(f'   추가: {len(valid_mappings)}개')
else:
    print('\n⚠️  추가할 매핑 없음')
