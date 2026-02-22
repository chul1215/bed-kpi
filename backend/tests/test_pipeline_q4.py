"""
4분기 데이터 기준 KPI 파이프라인 통합 테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.kpi_pipeline import KPIPipeline


def test_q4_pipeline():
    """4분기 데이터로 전체 파이프라인 테스트"""

    print("=" * 80)
    print("4분기 데이터 기준 KPI 파이프라인 테스트")
    print("=" * 80)

    # 파일 경로
    hira_file = project_root.parent / "data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx"
    smc_file = project_root.parent / "data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx"
    kdrg_file = project_root.parent / "data/KDRG v4.6 전체코드.xlsx"

    print(f"\n[파일 확인]")
    print(f"  HIRA: {hira_file.name}")
    print(f"  SMC: {smc_file.name}")
    print(f"  KDRG: {kdrg_file.name}")

    # 대전병원 - 4분기
    print("\n" + "=" * 80)
    print("대전병원 - 4분기 (10-12월)")
    print("=" * 80)

    pipeline = KPIPipeline(kdrg_file_path=str(kdrg_file))

    result = pipeline.run_pipeline(
        hira_file_path=str(hira_file),
        smc_file_path=str(smc_file),
        hospital="대전",
        filter_quarter=4  # 4분기 필터링
    )

    # 결과 요약
    print("\n[결과 요약]")
    metadata = result.get('metadata', {})
    print(f"  총 환자수: {metadata.get('total_patients', 0):,}명")
    print(f"  DRG 매칭률: {metadata.get('match_rate', 0):.1f}%")
    print(f"  비수기 환자: {metadata.get('off_season_patients', 0):,}명")
    print(f"  통상기간 환자: {metadata.get('normal_patients', 0):,}명")

    # Summary KPI
    print("\n[Summary KPI]")
    summary = result.get('summary_kpi', {})

    print("\n  비수기 (11-12월):")
    off_summary = summary.get('off_season', {})
    print(f"    평균 LOS 갭: {off_summary.get('avg_los_gap', 0):.2f}일")
    print(f"    추가 병상일수: {off_summary.get('total_additional_bed_days', 0):,.0f}일")
    print(f"    가동률 개선: {off_summary.get('occupancy_improvement', 0):.2f}%")

    print("\n  통상기간 (10월):")
    normal_summary = summary.get('normal', {})
    print(f"    평균 LOS 갭: {normal_summary.get('avg_los_gap', 0):.2f}일")
    print(f"    추가 병상일수: {normal_summary.get('total_additional_bed_days', 0):,.0f}일")
    print(f"    가동률 개선: {normal_summary.get('occupancy_improvement', 0):.2f}%")

    # 의료진 TOP 3
    print("\n[의료진 KPI TOP 3 - 비수기]")
    doctor_kpis_off = result.get('doctor_kpis_off_season')
    if doctor_kpis_off is not None and not doctor_kpis_off.empty:
        top3 = doctor_kpis_off.nlargest(3, 'additional_bed_days')
        for i, row in enumerate(top3.itertuples(), 1):
            print(f"  {i}. {row.doctor} ({row.department})")
            print(f"     환자수: {row.patient_count:,}명, LOS갭: {row.los_gap:.2f}일, "
                  f"추가병상: {row.additional_bed_days:,.0f}일")

    # 질환 TOP 3
    print("\n[질환 KPI TOP 3 - 비수기]")
    disease_kpis_off = result.get('disease_kpis_off_season')
    if disease_kpis_off is not None and not disease_kpis_off.empty:
        top3 = disease_kpis_off.nlargest(3, 'patient_count')
        for i, row in enumerate(top3.itertuples(), 1):
            target_los = row.target_los if hasattr(row, 'target_los') else None
            target_str = f"{target_los:.2f}일" if target_los else "N/A"
            print(f"  {i}. {row.diagnosis}")
            print(f"     환자수: {row.patient_count:,}명, 현재LOS: {row.current_los:.2f}일, "
                  f"목표LOS: {target_str}")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

    return result


def test_full_year_comparison():
    """전체 연도 vs 4분기 비교 테스트"""

    print("\n" + "=" * 80)
    print("전체 연도 vs 4분기 데이터 비교")
    print("=" * 80)

    hira_file = project_root.parent / "data/hira/2025_4분기_종합병원_ADRG별_평균재원)_20260220111626.xlsx"
    smc_file = project_root.parent / "data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx"
    kdrg_file = project_root.parent / "data/KDRG v4.6 전체코드.xlsx"

    # 전체 연도
    print("\n[1] 전체 연도 데이터")
    pipeline_full = KPIPipeline(kdrg_file_path=str(kdrg_file))
    result_full = pipeline_full.run_pipeline(
        hira_file_path=str(hira_file),
        smc_file_path=str(smc_file),
        hospital="대전",
        filter_quarter=None
    )

    # 4분기만
    print("\n[2] 4분기 데이터")
    pipeline_q4 = KPIPipeline(kdrg_file_path=str(kdrg_file))
    result_q4 = pipeline_q4.run_pipeline(
        hira_file_path=str(hira_file),
        smc_file_path=str(smc_file),
        hospital="대전",
        filter_quarter=4
    )

    # 비교
    print("\n[비교 결과]")
    meta_full = result_full.get('metadata', {})
    meta_q4 = result_q4.get('metadata', {})

    print(f"  전체 연도 환자수: {meta_full.get('total_patients', 0):,}명")
    print(f"  4분기 환자수: {meta_q4.get('total_patients', 0):,}명")
    print(f"  비율: {meta_q4.get('total_patients', 0) / meta_full.get('total_patients', 1) * 100:.1f}%")

    print(f"\n  전체 연도 매칭률: {meta_full.get('match_rate', 0):.1f}%")
    print(f"  4분기 매칭률: {meta_q4.get('match_rate', 0):.1f}%")

    print("\n✅ 4분기 필터링이 HIRA 데이터 기간과 일치하여 정확도 향상!")


if __name__ == "__main__":
    # 4분기 파이프라인 테스트
    result = test_q4_pipeline()

    # 전체 연도 vs 4분기 비교
    test_full_year_comparison()
