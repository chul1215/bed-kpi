"""진단명 수동 매핑 업데이트 - 미매칭 주요 진단명 추가"""
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

# 2. 추가할 매핑 (미매칭 주요 진단명)
new_mappings = [
    # 증상 코드 (KDRG에 없음)
    {'diagnosis': '어지럼증 및 어지럼', 'adrg_name': '두통'},  # R42 - 가장 가까운 증상
    {'diagnosis': '두통', 'adrg_name': '두통'},  # R51 - 직접 매칭

    # 악성 신생물 (수술 관련 ADRG 매칭)
    {'diagnosis': '갑상선의 악성 신생물', 'adrg_name': '주요 갑상선수술, 단측'},
    {'diagnosis': '담낭의 악성 신생물', 'adrg_name': '복강경을 이용한 전담낭절제술(총수담관탐구술 미동반)'},
    {'diagnosis': '전립선의 악성 신생물', 'adrg_name': '비뇨기계통의 악성 신생물'},

    # 일반 질환
    {'diagnosis': '치핵 및 항문주위정맥혈전증', 'adrg_name': '원형자동문합기를 이용한 치핵절제술'},
    {'diagnosis': '편도주위농양', 'adrg_name': '편도 및 아데노이드수술'},
    {'diagnosis': '급성 세뇨관-간질신장염', 'adrg_name': '신장 및 요로감염'},

    # 턱/구강 관련 (유길화 의사)
    {'diagnosis': '달리 분류되지 않은 구강영역의 낭', 'adrg_name': '주요 두경부 수술'},
    {'diagnosis': '턱의 기타 질환', 'adrg_name': '주요 두경부 수술'},

    # 기타 증상
    {'diagnosis': '천식', 'adrg_name': '천식'},
    {'diagnosis': '죽상경화증', 'adrg_name': '말초혈관 및 순환장애'},
]

# 3. HIRA에서 ADRG명 존재 확인
hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
hira_adrg_names = set(hira_df['adrg_name'].tolist())

print('\n=== 매핑 검증 ===')
valid_mappings = []

for mapping in new_mappings:
    diagnosis = mapping['diagnosis']
    adrg_name = mapping['adrg_name']

    # 이미 있는지 확인
    if diagnosis in current_df['diagnosis'].values:
        print(f'⏭️  {diagnosis:40s} → 이미 존재')
        continue

    # HIRA에 ADRG명이 있는지 확인
    if adrg_name in hira_adrg_names:
        valid_mappings.append(mapping)
        target_los = hira_df[hira_df['adrg_name'] == adrg_name].iloc[0]['target_los']
        print(f'✅ {diagnosis:40s} → {adrg_name} (LOS: {target_los:.2f})')
    else:
        print(f'❌ {diagnosis:40s} → ADRG명 없음: {adrg_name}')

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
