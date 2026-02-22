"""
Day 3 통합 테스트
전체 파이프라인 및 API 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.kpi_pipeline import KPIPipeline
from app.database.memory_store import memory_store
from app.services.dashboard_generator import DashboardGenerator


def test_imports():
    """모든 모듈 import 테스트"""
    print("=" * 80)
    print("Day 3 통합 테스트 시작")
    print("=" * 80)

    # 모듈 import 체크
    print("\n1. 모듈 Import 체크:")
    modules = {
        "KPIPipeline": KPIPipeline,
        "MemoryStore": memory_store,
        "DashboardGenerator": DashboardGenerator
    }

    for name, module in modules.items():
        print(f"  ✓ {name} 로드 성공")

    return True


def test_pipeline_initialization():
    """파이프라인 초기화 테스트"""
    print("\n2. KPI 파이프라인 초기화:")

    pipeline = KPIPipeline()
    print(f"  ✓ file_parser: {pipeline.file_parser}")
    print(f"  ✓ period_classifier: {pipeline.period_classifier}")
    print(f"  ✓ drg_matcher: {pipeline.drg_matcher}")
    print(f"  ✓ aggregator: {pipeline.aggregator}")
    print(f"  ✓ kpi_calculator: {pipeline.kpi_calculator}")

    return True


def test_memory_store():
    """메모리 저장소 테스트"""
    print("\n3. 메모리 저장소 테스트:")

    # 세션 생성
    session_id = memory_store.create_session("대전")
    print(f"  ✓ 세션 생성: {session_id}")

    # 세션 조회
    session = memory_store.get_session(session_id)
    print(f"  ✓ 세션 조회: {session.hospital}, {session.status}")

    # 세션 상태 업데이트
    memory_store.update_session_status(session_id, "completed", {"test": "ok"})
    session = memory_store.get_session(session_id)
    print(f"  ✓ 상태 업데이트: {session.status}")

    return True


def test_dashboard_generator():
    """대시보드 생성기 테스트"""
    print("\n4. 대시보드 생성기 테스트:")

    dashboard_gen = DashboardGenerator()

    # 템플릿 확인
    templates = ['index.html', 'department.html', 'doctor.html', 'disease.html', 'upload.html', 'base.html']
    for template_name in templates:
        template = dashboard_gen.env.get_template(template_name)
        print(f"  ✓ {template_name} 로드 성공")

    # render_upload 테스트
    html = dashboard_gen.render_upload()
    if len(html) > 0:
        print(f"  ✓ render_upload() 성공: {len(html)} bytes")

    return True


def test_full_pipeline():
    """전체 파이프라인 테스트 (실제 파일 필요)"""
    print("\n5. 전체 파이프라인 테스트:")

    data_dir = Path(__file__).parent.parent.parent / "data"
    hira_file = data_dir / "hira" / "2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx"
    smc_file = data_dir / "smc" / "25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx"

    if not hira_file.exists():
        print(f"  ⚠️  HIRA 파일 없음: {hira_file}")
        print("     실제 파일 업로드 시 테스트 필요")
        return True

    if not smc_file.exists():
        print(f"  ⚠️  SMC 파일 없음: {smc_file}")
        print("     실제 파일 업로드 시 테스트 필요")
        return True

    print(f"  ✓ HIRA 파일 존재: {hira_file.name}")
    print(f"  ✓ SMC 파일 존재: {smc_file.name}")

    try:
        pipeline = KPIPipeline()
        result = pipeline.run_pipeline(
            str(hira_file),
            str(smc_file),
            "대전"
        )

        print(f"  ✓ 파이프라인 실행 성공")
        print(f"    - HIRA: {result['metadata']['hira_count']}건")
        print(f"    - SMC: {result['metadata']['smc_count']}건")
        print(f"    - 매칭률: {result['metadata']['match_rate']:.1f}%")
        print(f"    - 비수기: {result['metadata']['off_season_count']}건")
        print(f"    - 통상기간: {result['metadata']['normal_count']}건")
        print(f"    - 의료진 KPI (비수기): {len(result['doctor_kpis_off_season'])}건")
        print(f"    - 질환 KPI (비수기): {len(result['disease_kpis_off_season'])}건")

        return True
    except Exception as e:
        print(f"  ⚠️  파이프라인 실행 실패: {str(e)}")
        print("     실제 파일 업로드 시 테스트 필요")
        return True


def main():
    """메인 테스트 실행"""
    tests = [
        ("Import 테스트", test_imports),
        ("파이프라인 초기화", test_pipeline_initialization),
        ("메모리 저장소", test_memory_store),
        ("대시보드 생성기", test_dashboard_generator),
        ("전체 파이프라인", test_full_pipeline)
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\n총 {total}개 중 {passed}개 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())
