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
from app.config import settings
import json

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

    # 대전/유성 병원별로 생성
    for hospital in ["대전", "유성"]:
        print(f"\n{'=' * 80}")
        print(f"{hospital}선병원 데이터 처리 시작")
        print(f"{'=' * 80}")

        # KPI 계산 (4분기 필터링)
        result = pipeline.run_pipeline(
            str(hira_file),
            str(smc_file),
            hospital,
            filter_quarter=4  # HIRA 4분기 데이터와 일치
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

            # 데이터 추출
            summary_kpi = result['summary_kpi']
            doctor_kpis = result[f'doctor_kpis_{period}']
            disease_kpis = result[f'disease_kpis_{period}']
            department_kpis = result[f'department_kpis_{period}']
            insights = result[f'insights_{period}']

            # 1. 홈 화면
            home_html = dashboard_gen.render_home(
                summary_kpi, doctor_kpis, insights, hospital, period
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

                # 해당 의료진의 질환 데이터 (샘플)
                doctor_html = dashboard_gen.render_doctor(
                    doctor_name, doctor_kpi, disease_kpis.head(5), hospital, period
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
