"""
자동 매칭 비활성화 확인 테스트
"""
import sys
sys.path.insert(0, 'backend')

from app.services.file_parser import FileParser
from app.services.adrg_mapper import ADRGMapper
from app.config import settings

# 1. ADRG 매퍼 초기화
mapper = ADRGMapper()
hira_file = 'data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'
hira_df = mapper.load_hira_adrg_table(hira_file)

mapper.load_icd10_to_adrg_mapping('data/mapping/icd10_to_adrg_from_kdrg46.xlsx')
mapper.load_manual_diagnosis_mapping('data/mapping/diagnosis_adrg_mapping.xlsx')

# 2. 문제 진단명 테스트
problem_diagnoses = [
    '허혈 뇌졸중 및 기타 비출혈성 뇌졸중',
    '세균성 폐렴',
    '기타 대퇴골 골절',
    '인플루엔자',
    '당뇨병'
]

print('자동 매칭 비활성화 테스트:')
print('=' * 80)

all_passed = True
for diag in problem_diagnoses:
    result = mapper.get_adrg_code(diag, None)
    status = '✅ None' if result is None else f'❌ {result}'
    print(f'{diag:40s} → {status}')
    if result is not None:
        all_passed = False

print('=' * 80)
if all_passed:
    print('✅ 모든 테스트 통과: 자동 매칭 비활성화됨')
else:
    print('❌ 일부 테스트 실패: 자동 매칭이 여전히 작동중')
print()

# 3. SMC 파일 로드 및 매칭 확인
print('SMC 파일 로드 및 ADRG 매칭 테스트:')
print('=' * 80)

smc_df = FileParser.parse_smc_file(settings.PRELOADED_SMC_FILE, filter_quarter=4, adrg_mapper=mapper)

# 문제 진단명들의 매칭 상태 확인
for diag in problem_diagnoses:
    rows = smc_df[smc_df['diagnosis'] == diag]
    if len(rows) > 0:
        matched = rows['adrg_code'].notna().sum()
        total = len(rows)
        print(f'{diag:40s}: {matched}/{total}명 매칭')
        if matched > 0:
            sample_code = rows[rows['adrg_code'].notna()].iloc[0]['adrg_code']
            print(f'  → ADRG 코드: {sample_code} ❌ (자동 매칭됨!)')
        else:
            print(f'  → 매칭 없음 ✅')
    else:
        print(f'{diag:40s}: 환자 없음')
    print()
