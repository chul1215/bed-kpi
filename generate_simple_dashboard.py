"""
간단한 대시보드 생성기 (목표 LOS 없이 현재 LOS만 표시)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.file_parser import FileParser
from app.services.adrg_mapper import ADRGMapper
from app.services.period_classifier import PeriodClassifier
from app.services.aggregator import Aggregator
from app.config import settings, PROJECT_ROOT
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import shutil


def generate_simple_dashboard():
    """목표 LOS 없이 현재 통계만 표시하는 대시보드 생성"""

    print("=" * 80)
    print("간단한 대시보드 생성 (목표 LOS 없이 현재 LOS만 표시)")
    print("=" * 80)

    # 출력 디렉토리
    output_dir = PROJECT_ROOT / "docs"
    output_dir.mkdir(exist_ok=True)

    # Jinja2 환경 설정
    env = Environment(loader=FileSystemLoader(PROJECT_ROOT / 'backend' / 'app' / 'templates'))

    # 1. HIRA 로드 (목표 LOS는 사용하지 않음)
    print("\n[1] HIRA ADRG 테이블 로드 (참고용)")
    mapper = ADRGMapper()
    hira_file = PROJECT_ROOT / 'data' / 'hira' / '2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'
    hira_df = mapper.load_hira_adrg_table(hira_file)
    print(f"✅ HIRA ADRG: {len(hira_df)}개 (참고용)")

    # 2. 매핑 로드 (ADRG명만 사용)
    print("\n[2] 매핑 파일 로드")
    mapper.load_icd10_to_adrg_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx')
    mapper.load_manual_diagnosis_mapping(PROJECT_ROOT / 'data' / 'mapping' / 'diagnosis_adrg_mapping.xlsx')
    print(f"✅ 매핑 로드 완료")

    # 3. SMC 데이터 로드
    print("\n[3] SMC 데이터 로드")
    smc_file = settings.PRELOADED_SMC_FILE
    smc_df = FileParser.parse_smc_file(smc_file, filter_quarter=4, adrg_mapper=mapper)

    # 기간 분류
    classifier = PeriodClassifier()
    smc_df['period'] = smc_df['discharge_date'].apply(classifier.classify_period)

    print(f"✅ SMC 데이터: {len(smc_df)}건")

    # 4. 병원별 대시보드 생성
    for hospital in ['대전', '유성']:
        print(f"\n{'=' * 80}")
        print(f"{hospital}선병원 대시보드 생성")
        print(f"{'=' * 80}")

        hospital_dir = output_dir / hospital
        hospital_dir.mkdir(exist_ok=True)

        for period, period_name in [('off_season', '비수기'), ('normal', '통상기간')]:
            print(f"\n📊 {period_name} 처리 중...")

            # 데이터 필터링
            period_df = smc_df[
                (smc_df['hospital'] == hospital) &
                (smc_df['period'] == period)
            ].copy()

            print(f"   환자수: {len(period_df)}명")

            # ADRG별 집계 (목표 LOS 없이)
            adrg_matched = period_df[period_df['adrg_code'].notna()]
            adrg_agg = Aggregator.aggregate_by_adrg(adrg_matched)

            print(f"   ADRG: {len(adrg_agg)}개")

            # 요약 통계
            total_patients = len(period_df)
            total_bed_days = period_df['los_days'].sum()
            avg_los = total_bed_days / total_patients if total_patients > 0 else 0

            # ADRG 매칭률
            matched_patients = len(adrg_matched)
            match_rate = (matched_patients / total_patients * 100) if total_patients > 0 else 0

            # 의료진별 집계
            doctor_agg = period_df.groupby('doctor').size().reset_index(name='patient_count')
            doctor_bed_days = period_df.groupby('doctor')['los_days'].sum().reset_index(name='bed_days')
            doctor_agg = doctor_agg.merge(doctor_bed_days, on='doctor')
            doctor_agg['avg_los'] = doctor_agg['bed_days'] / doctor_agg['patient_count']
            doctor_agg = doctor_agg.sort_values('patient_count', ascending=False)

            print(f"   의료진: {len(doctor_agg)}명")

            # HTML 생성
            template = env.get_template('simple_dashboard.html')
            html_content = template.render(
                hospital=hospital,
                period=period,
                period_name=period_name,
                # 요약 통계
                total_patients=total_patients,
                total_bed_days=int(total_bed_days),
                avg_los=avg_los,
                match_rate=match_rate,
                matched_patients=matched_patients,
                # ADRG TOP 10
                adrg_top10=adrg_agg.head(10).to_dict('records'),
                # 의료진 TOP 10
                doctor_top10=doctor_agg.head(10).to_dict('records')
            )

            # 저장
            output_file = hospital_dir / f"index_{period}.html"
            output_file.write_text(html_content, encoding='utf-8')
            print(f"   ✅ HTML: {hospital}/index_{period}.html")

    # 5. 루트 index.html (유성 비수기로 리다이렉트)
    root_index = output_dir / "index.html"
    root_index.write_text("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=유성/index_off_season.html">
    <title>리다이렉트 중...</title>
</head>
<body>
    <p>유성선병원 비수기 대시보드로 이동 중...</p>
</body>
</html>
""", encoding='utf-8')

    print(f"\n{'=' * 80}")
    print("✅ 간단한 대시보드 생성 완료!")
    print(f"{'=' * 80}")
    print()
    print(f"출력 디렉토리: {output_dir}")
    print(f"파일 확인: open {output_dir}/index.html")


if __name__ == "__main__":
    generate_simple_dashboard()
