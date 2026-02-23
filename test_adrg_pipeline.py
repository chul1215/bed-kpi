"""
ADRG 기반 파이프라인 테스트
"""
import sys
from pathlib import Path

# backend 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.file_parser import FileParser
from app.services.adrg_mapper import ADRGMapper
from app.services.period_classifier import PeriodClassifier
from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator
from app.config import settings, PROJECT_ROOT
import pandas as pd


def test_adrg_pipeline():
    """ADRG 기반 파이프라인 전체 테스트"""

    print("=" * 80)
    print("ADRG 기반 KPI 파이프라인 테스트")
    print("=" * 80)

    # 1. HIRA ADRG 테이블 로드
    print("\n[1] HIRA ADRG 테이블 로드")
    print("-" * 80)
    hira_file = PROJECT_ROOT / 'data' / 'hira' / '2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'

    mapper = ADRGMapper()
    hira_df = mapper.load_hira_adrg_table(hira_file)
    print(f"✅ HIRA ADRG 테이블: {len(hira_df)}개")
    print(f"   샘플: {hira_df.head(3).to_dict('records')}")

    # 2. ICD-10 매핑 로드 (있으면)
    print("\n[2] ICD-10 자동 매핑 로드")
    print("-" * 80)
    icd10_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx'
    if icd10_mapping_file.exists():
        mapper.load_icd10_to_adrg_mapping(icd10_mapping_file)
        print(f"✅ ICD-10 자동 매핑: {len(mapper.icd10_to_adrg)}개")
    else:
        print("⚠️  ICD-10 매핑 파일 없음 (선택 사항)")

    # 3. 수동 진단명 매핑 로드 (있으면)
    print("\n[3] 수동 진단명 매핑 로드")
    print("-" * 80)
    manual_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_adrg_mapping.xlsx'
    if manual_mapping_file.exists():
        mapper.load_manual_diagnosis_mapping(manual_mapping_file)
        print(f"✅ 수동 진단명 매핑: {len(mapper.diagnosis_to_adrg)}개")
    else:
        print("⚠️  수동 매핑 파일 없음 (선택 사항)")

    # 4. SMC 데이터 파싱 및 ADRG 매핑
    print("\n[4] SMC 데이터 파싱 및 ADRG 자동 매핑")
    print("-" * 80)
    smc_file = settings.PRELOADED_SMC_FILE
    smc_df = FileParser.parse_smc_file(smc_file, filter_quarter=4, adrg_mapper=mapper)

    print(f"✅ SMC 데이터: {len(smc_df)}건")
    matched_count = smc_df['adrg_code'].notna().sum()
    match_rate = (matched_count / len(smc_df)) * 100
    print(f"   ADRG 매칭: {matched_count}/{len(smc_df)} ({match_rate:.1f}%)")

    # 5. 기간 분류
    print("\n[5] 기간 분류 (비수기/통상기간)")
    print("-" * 80)
    smc_df = PeriodClassifier.add_period_column(smc_df)

    off_season_count = (smc_df['period'] == 'off_season').sum()
    normal_count = (smc_df['period'] == 'normal').sum()
    print(f"✅ 비수기: {off_season_count}건")
    print(f"✅ 통상기간: {normal_count}건")

    # 6. 대전 병원 비수기 데이터 집계
    print("\n[6] 대전 병원 비수기 데이터 집계 (ADRG 기준)")
    print("-" * 80)
    hospital = '대전'
    period = 'off_season'

    # ADRG 집계
    adrg_agg = Aggregator.aggregate_by_adrg(smc_df, hospital=hospital, period=period)
    print(f"✅ ADRG 집계: {len(adrg_agg)}개 ADRG")
    print(f"   환자수 합계: {adrg_agg['patient_count'].sum()}명")
    print(f"   병상일수 합계: {adrg_agg['total_bed_days'].sum()}일")

    # 의료진 집계
    doctor_agg = Aggregator.aggregate_by_doctor(smc_df, hospital=hospital, period=period)
    print(f"✅ 의료진 집계: {len(doctor_agg)}명")

    # 의료진-ADRG 교차 집계
    doctor_adrg_agg = Aggregator.aggregate_by_doctor_adrg(smc_df, hospital=hospital, period=period)
    print(f"✅ 의료진-ADRG 집계: {len(doctor_adrg_agg)}개 조합")

    # 7. KPI 계산
    print("\n[7] KPI 계산 (ADRG 기반)")
    print("-" * 80)

    # ADRG KPI (환자수 6명 이상만)
    adrg_kpis = []
    for _, row in adrg_agg.iterrows():
        kpi = KPICalculator.calculate_adrg_kpi(row)
        adrg_kpis.append(kpi)

    adrg_kpi_df = pd.DataFrame(adrg_kpis)
    valid_adrg_kpis = adrg_kpi_df[adrg_kpi_df['status'] == 'calculated']
    print(f"✅ ADRG KPI: {len(valid_adrg_kpis)}개 (환자 6명 이상)")

    if len(valid_adrg_kpis) > 0:
        print(f"   TOP 5 ADRG (환자수):")
        for idx, row in valid_adrg_kpis.head(5).iterrows():
            print(f"   - {row['adrg_code']} ({row['adrg_name']}): {row['patient_count']}명, "
                  f"LOS갭 {row['los_gap']:.2f}일, 추가병상 {row['additional_bed_days']:.0f}일")

    # ADRG 목표 LOS 매핑 생성 (NaN 제거)
    adrg_target_map = {}
    for _, row in adrg_kpi_df.iterrows():
        if pd.notna(row.get('target_los')):
            adrg_target_map[row['adrg_code']] = row['target_los']

    print(f"\n   ADRG 목표 LOS 매핑: {len(adrg_target_map)}개")

    # 의료진 KPI (ADRG 기반)
    doctor_kpis = []
    for _, row in doctor_agg.iterrows():
        kpi = KPICalculator.calculate_doctor_kpi_by_adrg(
            row,
            adrg_target_map,
            doctor_adrg_agg
        )
        doctor_kpis.append(kpi)

    doctor_kpi_df = pd.DataFrame(doctor_kpis)
    valid_doctor_kpis = doctor_kpi_df[doctor_kpi_df['status'] == 'calculated']
    print(f"\n✅ 의료진 KPI: {len(valid_doctor_kpis)}명 (계산 완료)")

    if len(valid_doctor_kpis) > 0:
        print(f"   TOP 5 의료진 (환자수):")
        for idx, row in valid_doctor_kpis.head(5).iterrows():
            print(f"   - {row['doctor']} ({row['department']}): {row['patient_count']}명, "
                  f"목표LOS {row['target_los']:.2f}일, LOS갭 {row['los_gap']:.2f}일, "
                  f"매칭률 {row.get('match_rate', 0):.1f}%")

    # 8. 정합성 검증
    print("\n[8] 데이터 정합성 검증")
    print("-" * 80)
    total_patients_adrg = adrg_agg['patient_count'].sum()
    total_patients_doctor = doctor_agg['patient_count'].sum()

    total_bed_days_adrg = adrg_agg['total_bed_days'].sum()
    total_bed_days_doctor = doctor_agg['total_bed_days'].sum()

    print(f"환자수 - ADRG: {total_patients_adrg}, 의료진: {total_patients_doctor}")
    print(f"병상일수 - ADRG: {total_bed_days_adrg:.0f}, 의료진: {total_bed_days_doctor:.0f}")

    # ADRG는 매칭된 것만 집계하므로 의료진보다 적을 수 있음
    if total_patients_adrg <= total_patients_doctor:
        print("✅ 정합성 검증 통과 (ADRG는 매칭된 환자만 포함)")
    else:
        print("⚠️  정합성 오류: ADRG 환자수가 의료진 환자수보다 많음")

    # 9. 매핑 템플릿 생성 (미매칭 진단명)
    print("\n[9] 매핑 템플릿 생성 (미매칭 진단명 TOP 100)")
    print("-" * 80)
    template_file = PROJECT_ROOT / 'data' / 'mapping' / 'adrg_mapping_template.xlsx'
    mapper.generate_mapping_template(smc_df, template_file, top_n=100)
    print(f"✅ 템플릿 생성: {template_file}")

    print("\n" + "=" * 80)
    print("✅ ADRG 기반 파이프라인 테스트 완료!")
    print("=" * 80)


if __name__ == '__main__':
    test_adrg_pipeline()
