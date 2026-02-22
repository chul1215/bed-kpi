"""
ICD-10 기반 DRG 매칭 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from app.services.file_parser import FileParser
from app.services.drg_matcher import DRGMatcher


def test_icd10_drg_matching():
    """ICD-10 기반 DRG 매칭 전체 파이프라인 테스트"""

    print("=" * 80)
    print("ICD-10 기반 DRG 매칭 테스트")
    print("=" * 80)

    # 1. 파일 경로
    smc_file = project_root.parent / "data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx"
    hira_file = project_root.parent / "data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx"
    kdrg_file = project_root.parent / "data/KDRG v4.6 전체코드.xlsx"

    print(f"\n[1] 파일 확인")
    print(f"  SMC: {smc_file.name}")
    print(f"  HIRA: {hira_file.name}")
    print(f"  KDRG: {kdrg_file.name}")

    # 2. HIRA 파일 파싱
    print(f"\n[2] HIRA 파일 파싱")
    hira_df = FileParser.parse_hira_file(str(hira_file))
    print(f"  ✅ HIRA 데이터: {len(hira_df)}건")

    # 3. SMC 파일 파싱 (Sheet1)
    print(f"\n[3] SMC Sheet1 파싱")
    smc_df = FileParser.parse_smc_file(str(smc_file))
    print(f"  ✅ SMC 환자 데이터: {len(smc_df)}건")
    print(f"  고유 진단명: {smc_df['diagnosis'].nunique()}개")

    # 4. SMC 병원별 시트에서 ICD-10 매핑 추출
    print(f"\n[4] ICD-10 매핑 추출 (병원별 시트)")
    icd_mapping = DRGMatcher.parse_hospital_sheet_to_icd_mapping(smc_file)
    print(f"  ✅ ICD-10 매핑: {len(icd_mapping)}개 진단명")

    # 상위 10개 출력
    print(f"\n  상위 10개 매핑:")
    for i, (diagnosis, icd) in enumerate(list(icd_mapping.items())[:10], 1):
        print(f"    {i}. {diagnosis[:30]:30s} → {icd}")

    # 5. DRG Matcher 초기화
    print(f"\n[5] DRG Matcher 초기화")
    matcher = DRGMatcher(kdrg_file)
    print(f"  ✅ ICD-10 → ADRG: {len(matcher.icd_to_adrg)}개 코드")

    # 6. HIRA ADRG 로드
    print(f"\n[6] HIRA ADRG 매핑 로드")
    matcher.load_hira_adrg_los(hira_df)
    print(f"  ✅ ADRG → LOS: {len(matcher.adrg_to_hira)}개")

    # 7. 상위 ICD-10 코드 매칭 테스트
    print(f"\n[7] 상위 ICD-10 코드 매칭 테스트")

    # Sheet1에서 환자수 상위 진단명 추출
    top_diagnoses = smc_df['diagnosis'].value_counts().head(10)

    print(f"\n  {'진단명':<35} {'ICD-10':<8} {'Target LOS':>12} {'환자수':>8}")
    print(f"  {'-'*70}")

    success_count = 0
    for diagnosis, count in top_diagnoses.items():
        icd_code = icd_mapping.get(diagnosis, 'N/A')
        target_los = matcher.get_target_los_by_icd(icd_code) if icd_code != 'N/A' else None

        if target_los is not None:
            success_count += 1
            status = f"{target_los:>12.2f}"
        else:
            status = f"{'매칭 실패':>12}"

        print(f"  {diagnosis[:35]:<35} {icd_code:<8} {status} {count:>8,}명")

    print(f"\n  매칭 성공: {success_count}/10")

    # 8. 전체 데이터 매칭
    print(f"\n[8] 전체 데이터 매칭")
    smc_matched = matcher.match_smc_with_icd(smc_df, icd_mapping)

    matched_patients = smc_matched['target_los'].notna().sum()
    total_patients = len(smc_matched)
    match_rate = matched_patients / total_patients * 100

    print(f"  ✅ 매칭 환자: {matched_patients:,}/{total_patients:,}명 ({match_rate:.1f}%)")

    # 9. 매칭 통계
    print(f"\n[9] 매칭 통계")
    stats = matcher.get_matching_statistics(smc_df, icd_mapping)

    print(f"  환자 기준:")
    print(f"    - 전체: {stats['total_patients']:,}명")
    print(f"    - 매칭: {stats['matched_patients']:,}명 ({stats['match_rate_patients']:.1f}%)")
    print(f"  진단명 기준:")
    print(f"    - 전체: {stats['total_diagnoses']}개")
    print(f"    - 매핑: {stats['mapped_diagnoses']}개 ({stats['match_rate_diagnoses']:.1f}%)")

    # 10. 매칭 실패 진단명 (상위 10개)
    print(f"\n[10] 매칭 실패 진단명 (상위 10개)")
    unmatched = smc_matched[smc_matched['target_los'].isna()]
    unmatched_counts = unmatched['diagnosis'].value_counts().head(10)

    for i, (diagnosis, count) in enumerate(unmatched_counts.items(), 1):
        icd_code = icd_mapping.get(diagnosis, 'N/A')
        print(f"  {i:2d}. {diagnosis[:40]:<40} (ICD: {icd_code:<6}) - {count:,}명")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

    return smc_matched, stats


if __name__ == "__main__":
    smc_matched, stats = test_icd10_drg_matching()
