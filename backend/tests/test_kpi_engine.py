"""
KPI 엔진 통합 테스트

Day 1의 전체 데이터 파이프라인을 검증합니다.
"""
import sys
from pathlib import Path

# Python path 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from app.services.file_parser import FileParser
from app.services.period_classifier import PeriodClassifier
from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator
from app.services.drg_matcher import DRGMatcher


def test_complete_pipeline():
    """
    전체 파이프라인 테스트 (Day 1)

    1. 파일 파싱
    2. 기간 분류
    3. DRG 매칭 (초기 매핑 생성)
    4. 데이터 집계
    5. KPI 계산
    6. 정합성 검증
    """
    print("\n" + "="*70)
    print("🚀 Day 1 전체 파이프라인 테스트 시작")
    print("="*70)

    # 1. 파일 파싱
    print("\n[1/6] 파일 파싱...")
    hira_file = Path("../data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx")
    smc_file = Path("../data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx")

    hira_df = FileParser.parse_hira_file(hira_file)
    smc_df = FileParser.parse_smc_file(smc_file)

    print(f"  ✅ HIRA: {len(hira_df)}건")
    print(f"  ✅ SMC: {len(smc_df):,}건")

    # 2. 기간 분류
    print("\n[2/6] 기간 분류...")
    smc_df = PeriodClassifier.add_period_column(smc_df)
    stats = PeriodClassifier.get_period_stats(smc_df)
    print(f"  ✅ 비수기: {stats['off_season']['count']:,}건")
    print(f"  ✅ 통상기간: {stats['normal']['count']:,}건")

    # 3. DRG 매칭
    print("\n[3/6] DRG 매칭...")
    mapping_file = Path("../data/mapping/diagnosis_drg_mapping.xlsx")
    mapping_file.parent.mkdir(parents=True, exist_ok=True)

    matcher = DRGMatcher()

    # 수동 매핑 테이블 로드 (있으면)
    if mapping_file.exists():
        matcher.load_manual_mapping(mapping_file)
        print(f"  ✅ 수동 매핑 테이블 로드: {len(matcher.diagnosis_to_adrg)}개")

    # SMC-HIRA 매칭
    smc_matched, disease_target_map = matcher.match_smc_to_hira(smc_df, hira_df)
    print(f"  ✅ 매칭 완료: {len(disease_target_map)}개 진단명")

    # 진단명 컬럼에 target_los 추가
    smc_df['target_los'] = smc_df['diagnosis'].map(disease_target_map)

    # 4. 데이터 집계 (비수기, 대전병원 기준)
    print("\n[4/6] 데이터 집계 (비수기, 대전병원)...")
    disease_agg = Aggregator.aggregate_by_disease(smc_df, hospital='대전', period='off_season')
    doctor_agg = Aggregator.aggregate_by_doctor(smc_df, hospital='대전', period='off_season')
    department_agg = Aggregator.aggregate_by_department(smc_df, hospital='대전', period='off_season')

    print(f"  ✅ 질환 집계: {len(disease_agg)}개 질환")
    print(f"  ✅ 의료진 집계: {len(doctor_agg)}명")
    print(f"  ✅ 진료과 집계: {len(department_agg)}개 과")

    # 5. KPI 계산
    print("\n[5/6] KPI 계산...")

    # 질환별 KPI
    disease_kpis = []
    for _, row in disease_agg.iterrows():
        kpi = KPICalculator.calculate_disease_kpi(row)
        disease_kpis.append(kpi)

    disease_kpis_df = pd.DataFrame(disease_kpis)
    calculated_count = len(disease_kpis_df[disease_kpis_df['status'] == 'calculated'])
    no_target_count = len(disease_kpis_df[disease_kpis_df['status'] == 'no_target_los'])

    print(f"  ✅ 질환별 KPI: {calculated_count}개 계산, {no_target_count}개 목표 없음")

    # 의료진-질환 집계 (의료진 KPI용)
    doctor_disease_agg = Aggregator.aggregate_by_doctor_disease(smc_df, hospital='대전', period='off_season')

    # 의료진별 KPI
    doctor_kpis = []
    for _, row in doctor_agg.iterrows():
        kpi = KPICalculator.calculate_doctor_kpi(row, disease_target_map, doctor_disease_agg)
        doctor_kpis.append(kpi)

    doctor_kpis_df = pd.DataFrame(doctor_kpis)
    doctor_calculated = len(doctor_kpis_df[doctor_kpis_df['status'] == 'calculated'])

    print(f"  ✅ 의료진별 KPI: {doctor_calculated}명 계산")

    # 요약 KPI (계산된 질환만)
    calculated_disease_kpis = disease_kpis_df[disease_kpis_df['status'] == 'calculated']
    if len(calculated_disease_kpis) > 0:
        summary_kpi = KPICalculator.calculate_summary_kpi(
            calculated_disease_kpis,
            bed_count=300,
            period_days=122  # 비수기
        )

        print(f"  ✅ 요약 KPI:")
        print(f"     - 평균 LOS 갭: {summary_kpi['average_los_gap']:.2f}일")
        print(f"     - 추가 병상일수: {summary_kpi['total_additional_bed_days']:.0f}일")
        print(f"     - 현재 가동률: {summary_kpi['current_utilization_rate']:.1f}%")
        print(f"     - 목표 가동률: {summary_kpi['target_utilization_rate']:.1f}%")

    # 6. 정합성 검증
    print("\n[6/6] 정합성 검증...")
    errors = Aggregator.calculate_consistency_error(
        disease_agg,
        doctor_agg,
        department_agg
    )

    if errors['is_consistent']:
        print("  ✅ 정합성 검증 통과!")
    else:
        print("  ⚠️ 정합성 오류:")
        print(f"     - 질환 vs 의료진 환자수 차: {errors['disease_doctor_patients']}")
        print(f"     - 질환 vs 진료과 환자수 차: {errors['disease_department_patients']}")

    # 최종 결과
    print("\n" + "="*70)
    print("✨ Day 1 파이프라인 테스트 완료!")
    print("="*70)
    print(f"\n📊 최종 데이터 요약:")
    print(f"  • HIRA 기준: {len(hira_df)}개 DRG")
    print(f"  • SMC 환자: {len(smc_df):,}명")
    print(f"  • 비수기(대전) 환자: {disease_agg['patient_count'].sum():,}명")
    print(f"  • 의료진: {len(doctor_agg)}명")
    print(f"  • 진료과: {len(department_agg)}개")
    print(f"  • 진단명: {len(disease_agg)}개")
    print(f"\n🎯 Day 2 준비 상태:")
    print(f"  ✅ 데이터 엔진 완성")
    print(f"  ✅ DRG 매핑 테이블 준비됨")
    print(f"  ⏳ HTML 대시보드 구현 예정")


if __name__ == "__main__":
    test_complete_pipeline()
