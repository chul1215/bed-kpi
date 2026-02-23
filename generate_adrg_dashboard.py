"""
ADRG 기반 정적 HTML 대시보드 생성기
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
from app.config import settings, PROJECT_ROOT
import pandas as pd
import json

def generate_adrg_dashboard():
    """ADRG 기반 정적 HTML 대시보드 생성"""

    print("=" * 80)
    print("ADRG 기반 정적 HTML 대시보드 생성")
    print("=" * 80)

    # 출력 디렉토리 생성
    output_dir = PROJECT_ROOT / "docs"
    output_dir.mkdir(exist_ok=True)

    # 1. HIRA ADRG 테이블 로드
    print("\n[1] HIRA ADRG 테이블 로드")
    hira_file = PROJECT_ROOT / 'data' / 'hira' / '2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx'

    mapper = ADRGMapper()
    hira_df = mapper.load_hira_adrg_table(hira_file)
    print(f"✅ HIRA ADRG: {len(hira_df)}개")

    # 2. 매핑 파일 로드
    print("\n[2] 매핑 파일 로드")

    # ICD-10 자동 매핑
    icd10_mapping_file = PROJECT_ROOT / 'data' / 'mapping' / 'icd10_to_adrg_from_kdrg46.xlsx'
    if icd10_mapping_file.exists():
        mapper.load_icd10_to_adrg_mapping(icd10_mapping_file)
        print(f"✅ ICD-10 자동 매핑: {len(mapper.icd10_to_adrg)}개")

    # 진단명 수동 매핑
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
    hospitals = ['대전', '유성']
    periods = [
        ('off_season', '비수기'),
        ('normal', '통상기간')
    ]

    print("\n[5] 병원별 × 기간별 대시보드 생성")
    print("-" * 80)

    for hospital in hospitals:
        hospital_dir = output_dir / hospital
        hospital_dir.mkdir(exist_ok=True)

        for period_code, period_name in periods:
            print(f"\n📊 {hospital} - {period_name}")

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

            # 요약 통계
            valid_adrg_kpis = adrg_kpi_df[adrg_kpi_df['status'] == 'calculated']
            valid_doctor_kpis = doctor_kpi_df[doctor_kpi_df['status'] == 'calculated']

            total_additional_bed_days = valid_adrg_kpis['additional_bed_days'].sum() if len(valid_adrg_kpis) > 0 else 0

            # 병상 수 및 기간 일수
            bed_count = settings.HOSPITAL_CONFIG[hospital]["bed_count"]
            period_days = 122 if period_code == 'off_season' else 243
            available_bed_days = bed_count * period_days

            utilization_gap = (total_additional_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0

            print(f"   유효 ADRG KPI: {len(valid_adrg_kpis)}개")
            print(f"   유효 의료진 KPI: {len(valid_doctor_kpis)}명")
            print(f"   추가 재원일수: {total_additional_bed_days:.0f}일")
            print(f"   가동률 개선: {utilization_gap:.1f}%")

            # JSON 파일 저장 (추후 JavaScript 로딩용)
            data = {
                'hospital': hospital,
                'period': period_code,
                'period_name': period_name,
                'summary': {
                    'total_patients': int(len(period_df)),
                    'matched_patients': int(period_df['adrg_code'].notna().sum()),
                    'match_rate': round(match_rate, 1),
                    'total_additional_bed_days': round(total_additional_bed_days, 0),
                    'utilization_gap': round(utilization_gap, 1),
                    'adrg_count': len(valid_adrg_kpis),
                    'doctor_count': len(valid_doctor_kpis)
                },
                'adrg_kpis': valid_adrg_kpis.to_dict('records')[:100],  # TOP 100
                'doctor_kpis': valid_doctor_kpis.to_dict('records')[:100]  # TOP 100
            }

            json_file = hospital_dir / f"kpi_data_{period_code}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"   ✅ JSON 저장: {json_file.relative_to(output_dir)}")

    # 6. 간단한 index.html 생성
    print("\n[6] index.html 생성")
    index_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>선메디컬센터 병상가동 KPI 대시보드 (ADRG 기반)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .hospital-section { margin-bottom: 40px; }
        .period-card { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">선메디컬센터 병상가동 KPI 대시보드</h1>
        <p class="lead">ADRG 코드 기반 KPI 산출 (2025년 4분기)</p>

        <div class="alert alert-info">
            <strong>매칭률:</strong> 58.1% (8,063명 중 4,688명 ADRG 매칭)
        </div>

        <div class="hospital-section">
            <h2>대전선병원</h2>
            <div class="row">
                <div class="col-md-6">
                    <div class="card period-card">
                        <div class="card-body">
                            <h5 class="card-title">비수기 (3-4월, 11-12월)</h5>
                            <p class="card-text">KPI 데이터를 확인하려면 JSON 파일을 참조하세요.</p>
                            <a href="대전/kpi_data_off_season.json" class="btn btn-primary">JSON 보기</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card period-card">
                        <div class="card-body">
                            <h5 class="card-title">통상기간 (1-2월, 5-10월)</h5>
                            <p class="card-text">KPI 데이터를 확인하려면 JSON 파일을 참조하세요.</p>
                            <a href="대전/kpi_data_normal.json" class="btn btn-primary">JSON 보기</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="hospital-section">
            <h2>유성선병원</h2>
            <div class="row">
                <div class="col-md-6">
                    <div class="card period-card">
                        <div class="card-body">
                            <h5 class="card-title">비수기 (3-4월, 11-12월)</h5>
                            <p class="card-text">KPI 데이터를 확인하려면 JSON 파일을 참조하세요.</p>
                            <a href="유성/kpi_data_off_season.json" class="btn btn-primary">JSON 보기</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card period-card">
                        <div class="card-body">
                            <h5 class="card-title">통상기간 (1-2월, 5-10월)</h5>
                            <p class="card-text">KPI 데이터를 확인하려면 JSON 파일을 참조하세요.</p>
                            <a href="유성/kpi_data_normal.json" class="btn btn-primary">JSON 보기</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <hr class="my-4">
        <p class="text-muted">
            <small>
                ADRG 기반 매칭: ICD-10 자동 매핑 (282개) + 진단명 수동 매핑 (132개)<br>
                생성 일시: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """
            </small>
        </p>
    </div>
</body>
</html>
"""

    index_file = output_dir / "index.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)

    print(f"✅ index.html 생성: {index_file}")

    print("\n" + "=" * 80)
    print("✅ ADRG 기반 대시보드 생성 완료!")
    print("=" * 80)
    print(f"\n출력 디렉토리: {output_dir}")
    print(f"파일 확인: open {output_dir}/index.html")
    print("\nGitHub Pages 배포:")
    print("  1. git add docs/")
    print("  2. git commit -m 'Update ADRG-based dashboard'")
    print("  3. git push origin main")
    print("  4. Settings > Pages > Source: main branch, /docs folder")


if __name__ == '__main__':
    generate_adrg_dashboard()
