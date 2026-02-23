"""
ADRG 기반 정적 HTML 대시보드 생성기 (기존 UI 유지)
GitHub Pages 배포용 정적 파일 생성
"""
import sys
from pathlib import Path

# 백엔드 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.file_parser import FileParser
from app.services.adrg_mapper import ADRGMapper
from app.services.period_classifier import PeriodClassifier
from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator
from app.services.dashboard_generator import DashboardGenerator
from app.config import settings, PROJECT_ROOT
import pandas as pd
import shutil


def calculate_doctor_adrg_kpis(
    doctor_name: str,
    smc_df,
    adrg_target_map: dict,
    hospital: str,
    period: str
):
    """
    특정 의료진의 ADRG별 KPI 계산

    Args:
        doctor_name: 의료진명
        smc_df: ADRG 매핑된 SMC 데이터프레임
        adrg_target_map: ADRG 코드 → 목표 LOS 매핑
        hospital: 병원명
        period: 기간

    Returns:
        ADRG별 KPI 데이터프레임
    """
    # 해당 의료진 + 병원 + 기간 필터링
    doctor_data = smc_df[
        (smc_df['doctor'] == doctor_name) &
        (smc_df['hospital'] == hospital) &
        (smc_df['period'] == period) &
        (smc_df['adrg_code'].notna())  # ADRG 매칭된 것만
    ]

    if len(doctor_data) == 0:
        return pd.DataFrame()

    # ADRG별 집계
    adrg_agg = doctor_data.groupby('adrg_code').agg({
        'los_days': ['sum', 'count', 'mean'],
        'adrg_name': 'first'
    }).reset_index()
    adrg_agg.columns = ['adrg_code', 'total_bed_days', 'patient_count', 'current_los', 'adrg_name']

    # 환자수 6명 미만 필터링
    adrg_agg = adrg_agg[adrg_agg['patient_count'] >= settings.MIN_PATIENT_COUNT]

    # 목표 LOS 추가
    adrg_agg['target_los'] = adrg_agg['adrg_code'].map(adrg_target_map)

    # KPI 계산
    adrg_kpis = []
    for _, row in adrg_agg.iterrows():
        kpi = KPICalculator.calculate_adrg_kpi(row)
        adrg_kpis.append(kpi)

    result_df = pd.DataFrame(adrg_kpis)

    # additional_bed_days 기준 정렬 (None 제외)
    if len(result_df) > 0 and 'status' in result_df.columns:
        result_df = result_df[result_df['status'] == 'calculated']
        if len(result_df) > 0:
            result_df = result_df.sort_values('additional_bed_days', ascending=False)

    return result_df


def generate_static_dashboard_adrg():
    """ADRG 기반 정적 HTML 대시보드 생성 (기존 UI 유지)"""

    print("=" * 80)
    print("ADRG 기반 정적 HTML 대시보드 생성 (기존 UI 유지)")
    print("=" * 80)

    # 출력 디렉토리 생성
    output_dir = PROJECT_ROOT / "docs"
    output_dir.mkdir(exist_ok=True)

    # DashboardGenerator 초기화
    dashboard_gen = DashboardGenerator()

    # 1. HIRA ADRG 테이블 로드
    print("\n[1] HIRA ADRG 테이블 로드")
    hira_file = PROJECT_ROOT / 'data' / 'hira' / '2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'

    mapper = ADRGMapper()
    hira_df = mapper.load_hira_adrg_table(hira_file)
    print(f"✅ HIRA ADRG: {len(hira_df)}개")

    # 2. 매핑 파일 로드
    print("\n[2] 매핑 파일 로드")

    # 진단명 수동 매핑만 사용 (ICD-10 매핑 제거됨)
    manual_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_adrg_mapping.xlsx'
    if manual_mapping_file.exists():
        mapper.load_manual_diagnosis_mapping(manual_mapping_file)
        print(f"✅ 진단명 수동 매핑: {len(mapper.diagnosis_to_adrg)}개")

    # 3. SMC 데이터 로드 및 ADRG 매핑
    print("\n[3] SMC 데이터 로드 및 ADRG 매핑")
    smc_file = settings.PRELOADED_SMC_FILE
    smc_df = FileParser.parse_smc_file(smc_file, filter_quarter=4, adrg_mapper=mapper)

    matched_count = smc_df['adrg_code'].notna().sum()
    match_rate = (matched_count / len(smc_df)) * 100
    print(f"✅ SMC 데이터: {len(smc_df)}건")
    print(f"   ADRG 매칭: {matched_count}/{len(smc_df)} ({match_rate:.1f}%)")

    # 4. 기간 분류
    print("\n[4] 기간 분류")
    smc_df = PeriodClassifier.add_period_column(smc_df)

    # 5. 병원별 × 기간별 대시보드 생성
    for hospital in ['대전', '유성']:
        print(f"\n{'=' * 80}")
        print(f"{hospital}선병원 HTML 대시보드 생성")
        print(f"{'=' * 80}")

        hospital_dir = output_dir / hospital
        hospital_dir.mkdir(exist_ok=True)

        # 하위 디렉토리 생성
        (hospital_dir / 'adrgs_off_season').mkdir(exist_ok=True)
        (hospital_dir / 'adrgs_normal').mkdir(exist_ok=True)
        (hospital_dir / 'doctors_off_season').mkdir(exist_ok=True)
        (hospital_dir / 'doctors_normal').mkdir(exist_ok=True)

        for period_code, period_name in [('off_season', '비수기'), ('normal', '통상기간')]:
            print(f"\n📊 {period_name} 처리 중...")

            # 필터링
            period_df = smc_df[
                (smc_df['hospital'] == hospital) &
                (smc_df['period'] == period_code)
            ].copy()

            print(f"   환자수: {len(period_df)}명")

            # ADRG 집계
            adrg_agg = Aggregator.aggregate_by_adrg(period_df)
            print(f"   ADRG: {len(adrg_agg)}개")

            # 의료진 집계
            doctor_agg = Aggregator.aggregate_by_doctor(period_df)
            print(f"   의료진: {len(doctor_agg)}명")

            # 의료진-ADRG 집계
            doctor_adrg_agg = Aggregator.aggregate_by_doctor_adrg(period_df)

            # ADRG KPI 계산
            adrg_kpis = []
            for _, row in adrg_agg.iterrows():
                kpi = KPICalculator.calculate_adrg_kpi(row)
                adrg_kpis.append(kpi)

            adrg_kpi_df = pd.DataFrame(adrg_kpis)

            # ADRG 목표 LOS 매핑 (NaN 제거)
            adrg_target_map = {}
            for _, row in adrg_kpi_df.iterrows():
                if pd.notna(row.get('target_los')):
                    adrg_target_map[row['adrg_code']] = row['target_los']

            # 의료진 KPI 계산
            doctor_kpis = []
            for _, row in doctor_agg.iterrows():
                kpi = KPICalculator.calculate_doctor_kpi_by_adrg(
                    row,
                    adrg_target_map,
                    doctor_adrg_agg
                )
                doctor_kpis.append(kpi)

            doctor_kpi_df = pd.DataFrame(doctor_kpis)

            # 진료과 집계 (추가)
            dept_agg = Aggregator.aggregate_by_department(period_df)

            # 요약 통계
            valid_adrg_kpis = adrg_kpi_df[adrg_kpi_df['status'] == 'calculated']
            valid_doctor_kpis = doctor_kpi_df[doctor_kpi_df['status'] == 'calculated']

            total_additional_bed_days = valid_adrg_kpis['additional_bed_days'].sum() if len(valid_adrg_kpis) > 0 else 0

            # 병상 수 및 기간 일수
            bed_count = settings.HOSPITAL_CONFIG[hospital]["bed_count"]
            period_days = 122 if period_code == 'off_season' else 243
            available_bed_days = bed_count * period_days

            utilization_gap = (total_additional_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0

            # 현재 가동률 계산
            total_current_bed_days = period_df['los_days'].sum()
            current_utilization_rate = (total_current_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0
            target_utilization_rate = current_utilization_rate + utilization_gap

            # 요약 KPI
            summary_kpi = {
                'total_additional_bed_days': round(total_additional_bed_days, 0),
                'utilization_gap': round(utilization_gap, 1),
                'current_utilization_rate': round(current_utilization_rate, 1),
                'target_utilization_rate': round(target_utilization_rate, 1),
                'patient_count': int(len(period_df)),
                'matched_count': int(period_df['adrg_code'].notna().sum()),
                'match_rate': round((period_df['adrg_code'].notna().sum() / len(period_df)) * 100, 1) if len(period_df) > 0 else 0
            }

            # 의료진별 ADRG 데이터 생성 (토글용)
            doctor_adrg_dict = {}
            for _, doctor_row in valid_doctor_kpis.iterrows():
                doctor_name = doctor_row['doctor']
                doctor_adrg_kpis = calculate_doctor_adrg_kpis(
                    doctor_name,
                    smc_df,
                    adrg_target_map,
                    hospital,
                    period_code
                )

                # ADRG 코드 → 진단명 형식으로 변환 (템플릿 호환)
                if len(doctor_adrg_kpis) > 0:
                    doctor_adrg_kpis_display = doctor_adrg_kpis.copy()
                    doctor_adrg_kpis_display['diagnosis'] = doctor_adrg_kpis_display.apply(
                        lambda row: f"{row['adrg_code']} ({row['adrg_name']})",
                        axis=1
                    )
                    doctor_adrg_dict[doctor_name] = doctor_adrg_kpis_display.to_dict('records')

            # 인사이트 (간단 버전)
            insights = {
                'total_patients': int(len(period_df)),
                'adrg_count': len(valid_adrg_kpis),
                'doctor_count': len(valid_doctor_kpis),
                'additional_bed_days': round(total_additional_bed_days, 0)
            }

            print(f"   유효 ADRG KPI: {len(valid_adrg_kpis)}개")
            print(f"   유효 의료진 KPI: {len(valid_doctor_kpis)}명")
            print(f"   추가 재원일수: {total_additional_bed_days:.0f}일")

            # 홈 HTML 생성용 ADRG 데이터 준비 (diagnosis 필드 추가)
            display_adrg_kpis = valid_adrg_kpis.copy()
            if len(display_adrg_kpis) > 0:
                display_adrg_kpis['diagnosis'] = display_adrg_kpis.apply(
                    lambda row: f"{row['adrg_code']} ({row['adrg_name']})",
                    axis=1
                )

            html_content = dashboard_gen.render_home(
                summary_kpi=summary_kpi,
                doctor_kpis=valid_doctor_kpis,  # DataFrame 전달
                disease_kpis=display_adrg_kpis,  # ADRG KPI (diagnosis 필드 포함)
                insights=[],  # 빈 리스트
                hospital=hospital,
                period=period_code,
                doctor_disease_data=doctor_adrg_dict
            )

            html_file = hospital_dir / f"index_{period_code}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"   ✅ 홈 HTML: {html_file.relative_to(output_dir)}")

            # 진료과 뷰는 스킵 (진료과 KPI 계산 미구현)
            print(f"   ⏭️  진료과 HTML: 스킵 (추후 구현)")

            # ADRG 상세 페이지는 스킵 (의료진 분포에 KPI 계산 미구현)
            print(f"   ⏭️  ADRG 상세: 스킵 (추후 구현)")

            # 의료진 상세 페이지 생성 (TOP 10)
            doctor_dir = hospital_dir / f"doctors_{period_code}"
            for idx, (_, doctor_row) in enumerate(valid_doctor_kpis.head(10).iterrows()):
                doctor_name = doctor_row['doctor']
                doctor_adrg_kpis = doctor_adrg_dict.get(doctor_name, [])

                # DataFrame으로 변환
                doctor_adrg_df = pd.DataFrame(doctor_adrg_kpis) if len(doctor_adrg_kpis) > 0 else pd.DataFrame()

                doctor_html = dashboard_gen.render_doctor(
                    doctor_name=doctor_name,
                    doctor_kpi=doctor_row.to_dict(),
                    disease_kpis=doctor_adrg_df,
                    hospital=hospital,
                    period=period_code
                )

                doctor_file = doctor_dir / f"{doctor_name}.html"
                with open(doctor_file, 'w', encoding='utf-8') as f:
                    f.write(doctor_html)

            print(f"   ✅ 의료진 상세: {len(valid_doctor_kpis.head(10))}명")

    # 메인 index.html 생성 (리다이렉트)
    main_index = output_dir / "index.html"
    redirect_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=대전/index_off_season.html">
    <title>선메디컬센터 병상가동 KPI 대시보드</title>
</head>
<body>
    <p>리다이렉트 중... <a href="대전/index_off_season.html">여기를 클릭하세요</a></p>
</body>
</html>
"""
    with open(main_index, 'w', encoding='utf-8') as f:
        f.write(redirect_html)

    print("\n" + "=" * 80)
    print("✅ ADRG 기반 대시보드 생성 완료!")
    print("=" * 80)
    print(f"\n출력 디렉토리: {output_dir}")
    print(f"파일 확인: open {output_dir}/index.html")


if __name__ == '__main__':
    generate_static_dashboard_adrg()
