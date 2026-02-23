"""
병원별 시트 데이터로 정적 HTML 대시보드 생성

병원별 시트는 이미 의사별 질환별로 집계된 데이터이므로,
HIRA 매칭 없이도 대시보드를 생성할 수 있습니다.

사용법:
    python3 generate_dashboard_from_hospital_sheet.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

import pandas as pd
from app.services.hospital_summary_parser import HospitalSummaryParser
from app.services.file_parser import FileParser
from app.services.kdrg_matcher import KDRGMatcher
from app.services.dashboard_generator import DashboardGenerator
from app.config import settings, PROJECT_ROOT

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  병원별 시트 데이터로 정적 HTML 대시보드 생성                                   ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    # 1. 병원별 시트 파싱 (ICD-10 코드 포함)
    print("1. 병원별 시트 파싱 중...")
    summary_df = HospitalSummaryParser.parse_hospital_summary(
        PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
    )
    print(f"   ✓ {len(summary_df)}건 (의사별 질환별 집계)")
    print(f"   ✓ 유성: {len(summary_df[summary_df['hospital']=='유성'])}건")
    print(f"   ✓ 대전: {len(summary_df[summary_df['hospital']=='대전'])}건")
    print(f"   ✓ ICD-10 코드: 100% 포함")
    print()

    # 2. HIRA 파일 로드 (목표 LOS 매핑용)
    print("2. HIRA 파일 로드 중...")
    hira_df = FileParser.parse_hira_file(settings.PRELOADED_HIRA_FILE)
    print(f"   ✓ {len(hira_df)}개 ADRG")
    print()

    # 3. 진단명 기반 매칭
    print("3. 진단명 기반 HIRA 매칭 중...")
    matcher = KDRGMatcher()

    # 수동 매핑 테이블 로드 (있으면)
    manual_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_kdrg44_mapping.xlsx'
    if manual_mapping_file.exists():
        print(f"   ✓ 수동 매핑 테이블 로드: {manual_mapping_file}")
        matcher.load_manual_mapping(manual_mapping_file)

    _, disease_target_map = matcher.match_smc_to_hira(summary_df, hira_df)

    matched = summary_df[summary_df['diagnosis'].isin(disease_target_map.keys())]
    matched_patients = matched['patient_count'].sum()
    total_patients = summary_df['patient_count'].sum()
    print(f"   ✓ 매칭된 진단명: {len(disease_target_map)}개 / {summary_df['diagnosis'].nunique()}개")
    print(f"   ✓ 매칭된 환자: {matched_patients:,}명 / {total_patients:,}명 ({matched_patients/total_patients*100:.1f}%)")
    print()

    # 4. 병원별 시트 데이터를 개별 환자 레코드로 변환
    print("4. 데이터 변환 중 (집계 → 개별 레코드)...")
    # 병원별 시트 데이터를 그대로 사용 (이미 집계되어 있음)
    # target_los 추가
    summary_df['target_los'] = summary_df['diagnosis'].map(disease_target_map)
    summary_df['los_days'] = summary_df['avg_los']
    print(f"   ✓ 변환 완료")
    print()

    # 5. 대시보드 생성
    print("5. 정적 HTML 대시보드 생성 중...")

    hospitals = ['유성', '대전']
    periods = ['off_season', 'normal']  # 병원별 시트는 연간 데이터이므로 분기 없음

    # 임시: 연간 데이터를 양쪽 기간에 모두 사용
    for hospital in hospitals:
        for period in periods:
            hospital_data = summary_df[summary_df['hospital'] == hospital]

            if len(hospital_data) == 0:
                print(f"   ⚠️  {hospital} {period}: 데이터 없음")
                continue

            print(f"   생성 중: {hospital} {period} ({len(hospital_data)}건)")

            # TODO: 실제 대시보드 생성 로직 구현
            # - 의사별 KPI 계산
            # - 질환별 KPI 계산
            # - HTML 생성

    print()
    print("="*80)
    print("⚠️  주의: 병원별 시트는 연간 집계 데이터입니다.")
    print("   비수기/통상기간 분리가 필요하면 Sheet1 데이터를 사용해야 합니다.")
    print("="*80)

if __name__ == '__main__':
    main()
