"""
ADRG 코드 기반 하이브리드 매칭 테스트

기존 진단명 기반 매칭 vs ADRG 코드 + 진단명 하이브리드 매칭 비교
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'backend'))

import pandas as pd
from app.services.file_parser import FileParser
from app.services.drg_matcher import DRGMatcher
from app.config import settings, PROJECT_ROOT


def main():
    print("=" * 80)
    print("ADRG 코드 기반 하이브리드 매칭 테스트")
    print("=" * 80)
    print()

    # 1. 파일 로드
    print("📂 파일 로드 중...")
    hira_file = settings.PRELOADED_HIRA_FILE
    smc_file = settings.PRELOADED_SMC_FILE

    print(f"   HIRA: {hira_file.name}")
    print(f"   SMC:  {smc_file.name}")
    print()

    # HIRA 파일 파싱
    hira_df = FileParser.parse_hira_file(hira_file)
    print(f"✅ HIRA 파싱 완료: {len(hira_df):,}건")
    print(f"   컬럼: {hira_df.columns.tolist()}")
    print()

    # SMC 파일 파싱
    smc_df = FileParser.parse_smc_file(smc_file)
    print(f"✅ SMC 파싱 완료: {len(smc_df):,}건")
    print(f"   컬럼: {smc_df.columns.tolist()}")

    # ADRG 컬럼 확인
    has_adrg = 'adrg_code' in smc_df.columns
    print(f"   ADRG 코드 컬럼: {'있음' if has_adrg else '없음'}")
    if has_adrg:
        adrg_valid = smc_df[smc_df['adrg_code'] != '미매핑']
        print(f"   유효 ADRG: {len(adrg_valid):,}건 ({len(adrg_valid)/len(smc_df)*100:.1f}%)")
    print()

    # 2. DRG Matcher 초기화
    print("🔧 DRG Matcher 초기화...")
    matcher = DRGMatcher()

    # 수동 매핑 테이블 로드
    mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'
    if mapping_file.exists():
        matcher.load_manual_mapping(mapping_file)
        print(f"✅ 수동 매핑 로드: {len(matcher.diagnosis_to_adrg)}개")
    print()

    # 3. 하이브리드 매칭 수행
    print("🎯 하이브리드 매칭 수행 중...")
    print("-" * 80)
    smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_df, hira_df)
    print("-" * 80)
    print()

    # 4. 상세 분석
    print("📊 상세 매칭 분석")
    print("-" * 80)

    # 병원별 분석
    for hospital in ['대전', '유성']:
        print(f"\n🏥 {hospital}선병원")
        hosp_df = smc_df[smc_df['hospital'] == hospital]

        # ADRG 코드로 매칭된 환자
        if has_adrg:
            adrg_matched = 0
            for _, row in hosp_df.iterrows():
                if row['diagnosis'] in disease_target_map:
                    adrg_code = row.get('adrg_code', '미매핑')
                    if adrg_code != '미매핑':
                        target_los = matcher.get_target_los(row['diagnosis'], adrg_code)
                        # ADRG 코드로 매칭되었는지 확인
                        adrg_3 = adrg_code[:3] if len(adrg_code) >= 3 else adrg_code
                        if adrg_3 in matcher.adrg_code_to_los:
                            adrg_matched += 1

            print(f"   전체 환자: {len(hosp_df):,}명")
            print(f"   ADRG 코드 매칭: {adrg_matched:,}명 ({adrg_matched/len(hosp_df)*100:.1f}%)")

            # 진단명으로만 매칭된 환자
            diagnosis_only = 0
            for diagnosis in hosp_df['diagnosis'].unique():
                if diagnosis in disease_target_map:
                    diag_df = hosp_df[hosp_df['diagnosis'] == diagnosis]
                    # ADRG 코드가 없거나 매칭 안 되는 경우
                    for _, row in diag_df.iterrows():
                        adrg_code = row.get('adrg_code', '미매핑')
                        adrg_3 = adrg_code[:3] if len(adrg_code) >= 3 else adrg_code
                        if adrg_code == '미매핑' or adrg_3 not in matcher.adrg_code_to_los:
                            diagnosis_only += 1

            print(f"   진단명 매칭: {diagnosis_only:,}명 ({diagnosis_only/len(hosp_df)*100:.1f}%)")

            total_matched = adrg_matched + diagnosis_only
            print(f"   총 매칭: {total_matched:,}명 ({total_matched/len(hosp_df)*100:.1f}%)")

    print()
    print("-" * 80)

    # 5. 매칭 안 된 진단명 TOP 10
    print("\n❌ 매칭 안 된 진단명 TOP 10")
    print("-" * 80)

    unmatched_df = smc_df[~smc_df['diagnosis'].isin(disease_target_map.keys())]
    if len(unmatched_df) > 0:
        unmatched_counts = unmatched_df['diagnosis'].value_counts().head(10)
        for diagnosis, count in unmatched_counts.items():
            adrg_sample = unmatched_df[unmatched_df['diagnosis'] == diagnosis]['adrg_code'].value_counts()
            adrg_info = f"(ADRG: {adrg_sample.index[0]})" if len(adrg_sample) > 0 and 'adrg_code' in unmatched_df.columns else ""
            print(f"   {diagnosis}: {count}명 {adrg_info}")
    else:
        print("   모든 진단명이 매칭되었습니다!")

    print()
    print("=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
