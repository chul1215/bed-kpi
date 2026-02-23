"""
정적 HTML 대시보드 생성기
GitHub Pages 배포용 정적 파일 생성
"""
import sys
from pathlib import Path

# 백엔드 경로 추가
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.kpi_pipeline import KPIPipeline
from app.services.dashboard_generator import DashboardGenerator
from app.services.kpi_calculator import KPICalculator
from app.services.aggregator import Aggregator
from app.config import settings
import json
import pandas as pd

def calculate_doctor_disease_kpis(
    doctor_name: str,
    smc_matched,
    disease_target_map: dict,
    hospital: str,
    period: str
):
    """
    특정 의료진의 질환별 KPI 계산

    Args:
        doctor_name: 의료진명
        smc_matched: 매칭된 SMC 데이터프레임
        disease_target_map: 진단명 → 목표 LOS 매핑
        hospital: 병원명
        period: 기간

    Returns:
        질환별 KPI 데이터프레임
    """
    # 해당 의료진 + 병원 + 기간 필터링
    doctor_data = smc_matched[
        (smc_matched['doctor'] == doctor_name) &
        (smc_matched['hospital'] == hospital) &
        (smc_matched['period'] == period)
    ]

    if len(doctor_data) == 0:
        return pd.DataFrame()

    # 질환별 집계
    disease_agg = doctor_data.groupby('diagnosis').agg({
        'los_days': ['sum', 'count', 'mean']
    }).reset_index()
    disease_agg.columns = ['diagnosis', 'total_bed_days', 'patient_count', 'current_los']

    # 환자수 6명 미만 필터링
    disease_agg = disease_agg[disease_agg['patient_count'] >= settings.MIN_PATIENT_COUNT]

    # 목표 LOS 추가
    disease_agg['target_los'] = disease_agg['diagnosis'].map(disease_target_map)

    # KPI 계산
    disease_kpis = []
    for _, row in disease_agg.iterrows():
        kpi = KPICalculator.calculate_disease_kpi(row)
        disease_kpis.append(kpi)

    result_df = pd.DataFrame(disease_kpis)

    # additional_bed_days 기준 정렬 (None 제외)
    if len(result_df) > 0 and 'status' in result_df.columns:
        result_df = result_df[result_df['status'] == 'calculated']
        if len(result_df) > 0:
            result_df = result_df.sort_values('additional_bed_days', ascending=False)

    return result_df


def generate_static_dashboard():
    """정적 HTML 대시보드 생성"""
    print("=" * 80)
    print("정적 HTML 대시보드 생성 시작")
    print("=" * 80)

    # 출력 디렉토리 생성
    output_dir = Path(__file__).parent / "docs"
    output_dir.mkdir(exist_ok=True)

    # KPI 파이프라인 실행 (KDRG 파일 포함)
    kdrg_file = settings.PRELOADED_KDRG_FILE
    pipeline = KPIPipeline(kdrg_file_path=str(kdrg_file))
    dashboard_gen = DashboardGenerator()

    hira_file = settings.PRELOADED_HIRA_FILE
    smc_file = settings.PRELOADED_SMC_FILE

    print(f"\n파일 로드:")
    print(f"  - HIRA: {hira_file.name}")
    print(f"  - SMC: {smc_file.name}")
    print(f"  - KDRG: {kdrg_file.name}")

    # HIRA 및 KDRG 매칭 준비 (전역으로 한번만 수행)
    from app.services.file_parser import FileParser
    from app.services.kdrg_matcher import KDRGMatcher
    from app.services.period_classifier import PeriodClassifier
    from app.config import PROJECT_ROOT

    # HIRA 파싱
    hira_df = FileParser.parse_hira_file(str(hira_file))

    # SMC 파싱 (4분기만)
    smc_df = FileParser.parse_smc_file(str(smc_file), filter_quarter=4)

    # KDRG Matcher 초기화 및 매칭
    kdrg_matcher = KDRGMatcher()
    kdrg_matcher.load_kdrg_table(str(kdrg_file))

    # ICD-10 매핑 로드 (KDRG 4.6 기반) - 최우선
    icd10_mapping_file = PROJECT_ROOT / "data" / "mapping" / "icd10_to_adrg_from_kdrg46.xlsx"
    if icd10_mapping_file.exists():
        print(f"\n✅ ICD-10 매핑 로드: {icd10_mapping_file.name}")
        kdrg_matcher.load_icd10_mapping(icd10_mapping_file)
    else:
        print(f"\n⚠️  ICD-10 매핑 파일 없음: {icd10_mapping_file}")

    # ⚠️ 주의: 병원별로 다른 매핑 파일 사용
    # - 대전: 주상병 매핑 제외 (원본)
    # - 유성: 주상병 매핑 포함 (주상병현황 그래프 반영)
    # 일단 공통 매핑만 로드 (병원별 분리는 각 병원 처리 시 수행)
    mapping_file = PROJECT_ROOT / "data" / "mapping" / "diagnosis_kdrg44_mapping.xlsx"
    if mapping_file.exists():
        kdrg_matcher.load_manual_mapping(mapping_file)

    # ICD-10 코드 포함된 데이터 로드 (병원별 시트)
    from app.services.hospital_summary_parser import HospitalSummaryParser
    hospital_summary_df = HospitalSummaryParser.parse_hospital_summary(
        PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
    )
    print(f"\n✅ 병원별 시트 로드: {len(hospital_summary_df)}건 (ICD-10 코드 100% 포함)")

    # Sheet1 데이터에 ICD-10 코드 매핑 (진단명 기준)
    diagnosis_to_icd10 = dict(zip(
        hospital_summary_df['diagnosis'],
        hospital_summary_df['icd10_code']
    ))
    smc_df['icd10_code'] = smc_df['diagnosis'].map(diagnosis_to_icd10)

    # ICD-10 커버리지 확인
    icd10_coverage = smc_df['icd10_code'].notna().sum()
    print(f"   ICD-10 커버리지: {icd10_coverage:,}명 / {len(smc_df):,}명 ({icd10_coverage/len(smc_df)*100:.1f}%)")

    # ICD-10 + 진단명 기반 매칭 (전체 데이터)
    smc_matched, disease_target_map = kdrg_matcher.match_smc_to_hira(smc_df, hira_df)

    # 기간 추가
    smc_matched = PeriodClassifier.add_period_column(smc_matched, 'discharge_date')

    # 대전/유성 병원별로 생성
    for hospital in ["대전", "유성"]:
        print(f"\n{'=' * 80}")
        print(f"{hospital}선병원 데이터 처리 시작")
        print(f"{'=' * 80}")

        # KPI 계산 (연간 전체 데이터)
        result = pipeline.run_pipeline(
            str(hira_file),
            str(smc_file),
            hospital,
            filter_quarter=None  # 연간 전체 데이터 사용
        )

        print(f"\n✅ KPI 계산 완료:")
        print(f"  - HIRA: {result['metadata']['hira_count']}건")
        print(f"  - SMC: {result['metadata']['smc_count']}건")
        print(f"  - 비수기: {result['metadata']['off_season_count']}건")
        print(f"  - 통상기간: {result['metadata']['normal_count']}건")

        # 병원별 디렉토리 생성
        hospital_dir = output_dir / hospital
        hospital_dir.mkdir(exist_ok=True)

        # 비수기/통상기간별로 HTML 생성
        for period in ["off_season", "normal"]:
            period_name = "비수기" if period == "off_season" else "통상기간"
            print(f"\n{period_name} HTML 생성 중...")

            # 데이터 추출 (기간별)
            summary_kpi = result[f'summary_kpi_{period}']
            doctor_kpis = result[f'doctor_kpis_{period}']
            disease_kpis = result[f'disease_kpis_{period}']
            department_kpis = result[f'department_kpis_{period}']
            insights = result[f'insights_{period}']

            # 의료진별 질환 데이터 생성 (토글용) - 모든 의료진
            doctor_disease_dict = {}
            valid_doctors = doctor_kpis[doctor_kpis['status'] == 'calculated']

            # 모든 의료진에 대해 질환 데이터 생성
            for _, doctor_row in valid_doctors.iterrows():
                doctor_name = doctor_row['doctor']
                doctor_disease_kpis = calculate_doctor_disease_kpis(
                    doctor_name,
                    smc_matched,
                    disease_target_map,
                    hospital,
                    period
                )
                if len(doctor_disease_kpis) > 0:
                    doctor_disease_dict[doctor_name] = doctor_disease_kpis.head(10).to_dict('records')

            # 1. 홈 화면
            home_html = dashboard_gen.render_home(
                summary_kpi, doctor_kpis, disease_kpis, insights, hospital, period, doctor_disease_dict
            )

            # 정적 HTML용 네비게이션 스크립트 생성
            nav_script = f"""
        // 정적 HTML용 네비게이션 (파일 경로 기반)
        function switchHospital(targetHospital) {{
            const currentPeriod = '{period}';
            const hospitalMap = {{'대전': '대전', '유성': '유성'}};
            const path = `../${{hospitalMap[targetHospital]}}/index_${{currentPeriod}}.html`;
            window.location.href = path;
        }}

        function switchPeriod(targetPeriod) {{
            const currentHospital = '{hospital}';
            const path = `index_${{targetPeriod}}.html`;
            window.location.href = path;
        }}
    """

            # 기존 네비게이션 스크립트 교체
            home_html = home_html.replace(
                """        // 병원 전환
        function switchHospital(hospital) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('hospital', hospital);
            window.location.search = urlParams.toString();
        }

        // 기간 전환
        function switchPeriod(period) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('period', period);
            window.location.search = urlParams.toString();
        }""",
                nav_script
            )

            # 절대 경로를 상대 경로로 변환 (같은 디렉토리 레벨)
            home_html = home_html.replace('href="/upload"', f'href="index_{period}.html"')
            home_html = home_html.replace('href="/"', f'href="index_{period}.html"')
            home_html = home_html.replace('href="/department"', f'href="department_{period}.html"')
            home_html = home_html.replace('href="/doctor"', f'href="index_{period}.html"')
            home_html = home_html.replace('href="/disease"', f'href="index_{period}.html"')
            home_html = home_html.replace("window.location.href='/upload'", f"window.location.href='index_{period}.html'")

            output_file = hospital_dir / f"index_{period}.html"
            output_file.write_text(home_html, encoding='utf-8')
            print(f"  ✓ {output_file.name}")

            # 2. 진료과 뷰
            doctor_kpis_by_dept = {}
            for dept in department_kpis['department'].unique():
                doctor_kpis_by_dept[dept] = doctor_kpis[doctor_kpis['department'] == dept]

            dept_html = dashboard_gen.render_department(
                department_kpis, doctor_kpis_by_dept, hospital, period
            )

            # 정적 HTML용 네비게이션 스크립트 주입
            dept_html = dept_html.replace(
                """        // 병원 전환
        function switchHospital(hospital) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('hospital', hospital);
            window.location.search = urlParams.toString();
        }

        // 기간 전환
        function switchPeriod(period) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('period', period);
            window.location.search = urlParams.toString();
        }""",
                nav_script
            )

            # 절대 경로를 상대 경로로 변환 (같은 디렉토리 레벨)
            dept_html = dept_html.replace('href="/upload"', f'href="index_{period}.html"')
            dept_html = dept_html.replace('href="/"', f'href="index_{period}.html"')
            dept_html = dept_html.replace('href="/department"', f'href="department_{period}.html"')
            dept_html = dept_html.replace('href="/doctor"', f'href="index_{period}.html"')
            dept_html = dept_html.replace('href="/disease"', f'href="index_{period}.html"')
            dept_html = dept_html.replace("window.location.href='/upload'", f"window.location.href='index_{period}.html'")

            output_file = hospital_dir / f"department_{period}.html"
            output_file.write_text(dept_html, encoding='utf-8')
            print(f"  ✓ {output_file.name}")

            # 3. 의료진 상세 (상위 10명만)
            doctors_dir = hospital_dir / f"doctors_{period}"
            doctors_dir.mkdir(exist_ok=True)

            # 서브디렉토리용 네비게이션 스크립트 (상위 디렉토리로 이동)
            nav_script_subdir = f"""
        // 정적 HTML용 네비게이션 (서브디렉토리에서)
        function switchHospital(targetHospital) {{
            const currentPeriod = '{period}';
            const hospitalMap = {{'대전': '대전', '유성': '유성'}};
            const path = `../../${{hospitalMap[targetHospital]}}/index_${{currentPeriod}}.html`;
            window.location.href = path;
        }}

        function switchPeriod(targetPeriod) {{
            const currentHospital = '{hospital}';
            const path = `../index_${{targetPeriod}}.html`;
            window.location.href = path;
        }}
    """

            valid_doctors = doctor_kpis[doctor_kpis['status'] == 'calculated']
            top_doctors = valid_doctors.nlargest(10, 'additional_bed_days')

            for _, doctor_row in top_doctors.iterrows():
                doctor_name = doctor_row['doctor']
                doctor_kpi = doctor_row.to_dict()

                # 해당 의료진의 질환별 KPI 계산 (전역 smc_matched, disease_target_map 사용)
                doctor_disease_kpis = calculate_doctor_disease_kpis(
                    doctor_name,
                    smc_matched,
                    disease_target_map,
                    hospital,
                    period
                )

                doctor_html = dashboard_gen.render_doctor(
                    doctor_name, doctor_kpi, doctor_disease_kpis, hospital, period
                )

                # 정적 HTML용 네비게이션 스크립트 주입
                doctor_html = doctor_html.replace(
                    """        // 병원 전환
        function switchHospital(hospital) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('hospital', hospital);
            window.location.search = urlParams.toString();
        }

        // 기간 전환
        function switchPeriod(period) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('period', period);
            window.location.search = urlParams.toString();
        }""",
                    nav_script_subdir
                )

                # 절대 경로를 상대 경로로 변환 (서브디렉토리에서 상위로)
                doctor_html = doctor_html.replace('href="/upload"', f'href="../index_{period}.html"')
                doctor_html = doctor_html.replace('href="/"', f'href="../index_{period}.html"')
                doctor_html = doctor_html.replace('href="/department"', f'href="../department_{period}.html"')
                doctor_html = doctor_html.replace('href="/doctor"', f'href="../index_{period}.html"')
                doctor_html = doctor_html.replace('href="/disease"', f'href="../index_{period}.html"')
                doctor_html = doctor_html.replace("window.location.href='/upload'", f"window.location.href='../index_{period}.html'")

                safe_name = doctor_name.replace(' ', '_').replace('/', '_')
                output_file = doctors_dir / f"{safe_name}.html"
                output_file.write_text(doctor_html, encoding='utf-8')

            print(f"  ✓ doctors_{period}/ (10명)")

            # 4. 질환 뷰 (상위 10개만)
            diseases_dir = hospital_dir / f"diseases_{period}"
            diseases_dir.mkdir(exist_ok=True)

            valid_diseases = disease_kpis[disease_kpis['status'] == 'calculated']
            top_diseases = valid_diseases.nlargest(10, 'patient_count')

            for _, disease_row in top_diseases.iterrows():
                disease_name = disease_row['diagnosis']
                disease_info = disease_row.to_dict()

                disease_html = dashboard_gen.render_disease(
                    disease_name, disease_info, doctor_kpis.head(5), hospital, period
                )

                # 정적 HTML용 네비게이션 스크립트 주입 (서브디렉토리용)
                disease_html = disease_html.replace(
                    """        // 병원 전환
        function switchHospital(hospital) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('hospital', hospital);
            window.location.search = urlParams.toString();
        }

        // 기간 전환
        function switchPeriod(period) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('period', period);
            window.location.search = urlParams.toString();
        }""",
                    nav_script_subdir
                )

                # 절대 경로를 상대 경로로 변환 (서브디렉토리에서 상위로)
                disease_html = disease_html.replace('href="/upload"', f'href="../index_{period}.html"')
                disease_html = disease_html.replace('href="/"', f'href="../index_{period}.html"')
                disease_html = disease_html.replace('href="/department"', f'href="../department_{period}.html"')
                disease_html = disease_html.replace('href="/doctor"', f'href="../index_{period}.html"')
                disease_html = disease_html.replace('href="/disease"', f'href="../index_{period}.html"')
                disease_html = disease_html.replace("window.location.href='/upload'", f"window.location.href='../index_{period}.html'")

                safe_name = disease_name.replace(' ', '_').replace('/', '_')
                output_file = diseases_dir / f"{safe_name}.html"
                output_file.write_text(disease_html, encoding='utf-8')

            print(f"  ✓ diseases_{period}/ (10개)")

        print(f"\n✅ {hospital}선병원 HTML 생성 완료")

    # 인덱스 페이지 생성 (리디렉션)
    index_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="0; url=대전/index_off_season.html">
    <title>선메디컬센터 병상가동 KPI 대시보드</title>
</head>
<body>
    <p>대시보드로 이동 중...</p>
    <p>자동으로 이동하지 않으면 <a href="대전/index_off_season.html">여기</a>를 클릭하세요.</p>
</body>
</html>
"""
    (output_dir / "index.html").write_text(index_html, encoding='utf-8')
    print(f"\n✓ docs/index.html (리디렉션)")

    # README 생성
    readme = """# 선메디컬센터 병상가동 KPI 대시보드

## 페이지 구조

### 대전선병원
- [비수기 (3-4월, 11-12월)](대전/index_off_season.html)
- [통상기간 (1-2월, 5-10월)](대전/index_normal.html)
- [진료과 뷰 - 비수기](대전/department_off_season.html)
- [진료과 뷰 - 통상기간](대전/department_normal.html)

### 유성선병원
- [비수기 (3-4월, 11-12월)](유성/index_off_season.html)
- [통상기간 (1-2월, 5-10월)](유성/index_normal.html)
- [진료과 뷰 - 비수기](유성/department_off_season.html)
- [진료과 뷰 - 통상기간](유성/department_normal.html)

## 배포 방법

이 `docs/` 폴더를 GitHub Pages로 배포하면 됩니다.

### GitHub 설정
1. Repository Settings
2. Pages 메뉴
3. Source: `main` branch, `/docs` folder
4. Save

배포 URL: `https://username.github.io/repository-name/`
"""
    (output_dir / "README.md").write_text(readme, encoding='utf-8')
    print("✓ docs/README.md")

    print("\n" + "=" * 80)
    print("정적 HTML 대시보드 생성 완료!")
    print("=" * 80)
    print(f"\n출력 디렉토리: {output_dir.absolute()}")
    print("\n생성된 파일:")
    print("  - docs/index.html (리디렉션)")
    print("  - docs/대전/index_off_season.html")
    print("  - docs/대전/index_normal.html")
    print("  - docs/대전/department_off_season.html")
    print("  - docs/대전/department_normal.html")
    print("  - docs/대전/doctors_off_season/*.html (10개)")
    print("  - docs/대전/doctors_normal/*.html (10개)")
    print("  - docs/대전/diseases_off_season/*.html (10개)")
    print("  - docs/대전/diseases_normal/*.html (10개)")
    print("  - docs/유성/... (동일 구조)")
    print("\nGitHub Pages 배포: docs/ 폴더를 커밋 후 Settings > Pages에서 설정")


if __name__ == "__main__":
    generate_static_dashboard()
