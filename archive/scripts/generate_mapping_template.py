"""
KDRG 4.4 매핑 템플릿 생성 스크립트

상위 N개 진단명에 대해 매핑 템플릿을 생성합니다.
생성된 템플릿 파일을 수동으로 편집하여 diagnosis_kdrg44_mapping.xlsx로 저장하세요.

사용법:
    python3 generate_mapping_template.py --top-n 100
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path

# backend 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.kdrg_matcher import KDRGMatcher
from app.services.file_parser import FileParser
from app.config import settings, PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description='KDRG 4.4 매핑 템플릿 생성')
    parser.add_argument('--top-n', type=int, default=100, help='상위 진단명 개수 (기본값: 100)')
    parser.add_argument('--output', type=str, default=None, help='출력 파일 경로')
    args = parser.parse_args()

    # 출력 파일 경로
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping_template.xlsx'

    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  KDRG 4.4 매핑 템플릿 생성                                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

상위 {args.top_n}개 진단명에 대한 매핑 템플릿을 생성합니다.

출력 파일: {output_file}
""")

    # 1. SMC 파일 로드
    print("1. SMC 파일 로드 중...")
    smc_df = FileParser.parse_smc_file(settings.PRELOADED_SMC_FILE)
    print(f"   ✓ {len(smc_df):,}명 환자 로드")
    print(f"   ✓ {len(smc_df['diagnosis'].unique())}개 고유 진단명")

    # 2. HIRA 파일 로드
    print("\n2. HIRA 파일 로드 중...")
    hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
    print(f"   ✓ {len(hira_df):,}개 ADRG 로드")

    # 3. 매핑 템플릿 생성
    print(f"\n3. 상위 {args.top_n}개 진단명 매핑 템플릿 생성 중...")
    matcher = KDRGMatcher()
    matcher.match_smc_to_hira(smc_df, hira_df)  # ADRG→HIRA 매핑 생성

    matcher.generate_mapping_template(
        smc_df,
        hira_df,
        output_file,
        top_n=args.top_n
    )

    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  매핑 템플릿 생성 완료                                                       ║
╚══════════════════════════════════════════════════════════════════════════╝

출력 파일: {output_file}

다음 단계:
1. 엑셀 파일 열기: {output_file}
2. "매핑템플릿" 시트에서 'adrg_name' 컬럼 작성
   - 'suggested_adrg' 컬럼 참조 (자동 제안)
   - 'ADRG목록' 시트에서 적절한 ADRG명 검색
3. 완성된 파일을 다음 경로로 저장:
   {PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'}
4. 대시보드 재생성:
   python3 generate_static_dashboard.py

주의사항:
- 'adrg_name' 컬럼은 반드시 HIRA 파일의 ADRG명과 정확히 일치해야 합니다.
- 'ADRG목록' 시트에서 ADRG명을 복사하여 사용하세요.
- 매칭이 어려운 진단명은 비워두거나 가장 유사한 ADRG명을 선택하세요.
""")


if __name__ == '__main__':
    main()
