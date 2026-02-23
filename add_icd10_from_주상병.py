#!/usr/bin/env python3
"""
주상병현황 그래프 데이터를 활용한 ICD-10 코드 추가 스크립트

주상병현황 파일에서 추출한 ICD-10 코드와 ADRG 매핑을
SMC 병원자료에 추가하여 매칭률을 개선합니다.

실행:
    python3 add_icd10_from_주상병.py
"""

import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT / 'backend'))

from app.services.file_parser import FileParser
from app.config import settings


def main():
    print("=== 주상병현황 기반 ICD-10 코드 추가 ===\n")

    # 1. 주상병 완전 매칭 데이터 로드
    주상병_매칭_파일 = PROJECT_ROOT / 'data' / 'mapping' / '주상병_완전매칭.csv'
    if not 주상병_매칭_파일.exists():
        print(f"❌ 파일 없음: {주상병_매칭_파일}")
        print("먼저 주상병현황 데이터를 분석하여 매칭 파일을 생성하세요.")
        return

    df_주상병 = pd.read_csv(주상병_매칭_파일)
    print(f"✅ 주상병 매칭 데이터 로드: {len(df_주상병)}건\n")

    # 2. ICD-10 → ADRG 매핑 딕셔너리 생성
    icd10_to_adrg = {}
    for _, row in df_주상병.iterrows():
        icd10_code = row['ICD10코드']
        icd10_name = row['ICD10명']
        adrg_name = row['ADRG명']

        # ICD-10 코드 기반 매핑
        icd10_to_adrg[icd10_code] = adrg_name

        # ICD-10 진단명 기반 매핑 (키워드)
        # 예: "어지럼증및어지럼" → "평형장애"
        icd10_to_adrg[icd10_name] = adrg_name

    print(f"✅ ICD-10 → ADRG 매핑 딕셔너리 생성: {len(icd10_to_adrg)}개 항목\n")

    # 3. 기존 매핑 파일 로드
    mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'
    df_기존매핑 = pd.read_excel(mapping_file)

    print(f"✅ 기존 매핑 파일 로드: {len(df_기존매핑)}건")
    print(f"   컬럼: {list(df_기존매핑.columns)}\n")

    # 4. 주상병 ICD-10 기반 새로운 매핑 추가
    새로운_매핑 = []

    for icd10_code, adrg_name in icd10_to_adrg.items():
        # ICD-10 코드인 경우만 (진단명은 제외)
        if len(str(icd10_code)) <= 6 and str(icd10_code)[0].isalpha():
            # 기존 매핑에 없는 경우만 추가
            existing = df_기존매핑[df_기존매핑['diagnosis'] == icd10_code]
            if len(existing) == 0:
                새로운_매핑.append({
                    'diagnosis': icd10_code,
                    'adrg_name': adrg_name,
                    'source': '주상병현황'
                })

    print(f"✅ 새로운 ICD-10 기반 매핑: {len(새로운_매핑)}건\n")

    # 5. 기존 매핑과 병합
    if 새로운_매핑:
        df_새로운 = pd.DataFrame(새로운_매핑)

        # 기존 매핑에 'source' 컬럼 추가 (없는 경우)
        if 'source' not in df_기존매핑.columns:
            df_기존매핑['source'] = 'manual'

        # 병합
        df_통합 = pd.concat([df_기존매핑, df_새로운], ignore_index=True)

        # 중복 제거 (diagnosis 기준)
        df_통합 = df_통합.drop_duplicates(subset=['diagnosis'], keep='first')

        print(f"✅ 통합 매핑: {len(df_통합)}건 (기존 {len(df_기존매핑)} + 신규 {len(새로운_매핑)})")
        print(f"   중복 제거 후: {len(df_통합)}건\n")

        # 6. 저장
        output_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping_주상병추가.xlsx'
        df_통합.to_excel(output_file, index=False)
        print(f"✅ 저장 완료: {output_file}")

        # 7. 요약
        print("\n=== 추가된 ICD-10 코드 ===")
        print(df_새로운[['diagnosis', 'adrg_name']].to_string(index=False))

    else:
        print("⚠️  추가할 새로운 매핑이 없습니다.")

    # 8. 주상병 ICD-10 진단명 분석
    print("\n\n=== 주상병 ICD-10 진단명 키워드 분석 ===")
    print("진단명 기반 매칭을 위한 키워드:")

    for _, row in df_주상병.iterrows():
        icd10_name = row['ICD10명']
        adrg_name = row['ADRG명']
        count = row['건수']

        # 긴 진단명에서 핵심 키워드 추출
        keywords = []
        if '위장염' in icd10_name or '결장염' in icd10_name or '장염' in icd10_name:
            keywords.append('장염 관련')
        if '어지럼' in icd10_name or '현기증' in icd10_name:
            keywords.append('현기증 관련')
        if '게실' in icd10_name:
            keywords.append('게실병 관련')

        if keywords:
            print(f"  {icd10_name[:30]:30s} → {adrg_name:10s} ({', '.join(keywords)}, {count}건)")


if __name__ == '__main__':
    main()
