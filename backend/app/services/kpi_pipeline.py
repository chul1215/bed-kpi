"""
KPI 산출 파이프라인 통합 서비스
Day 1의 모든 서비스를 통합하여 실행
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List
import pandas as pd
import logging

from app.services.file_parser import FileParser
from app.services.period_classifier import PeriodClassifier
from app.services.kdrg_matcher import KDRGMatcher
from app.services.aggregator import Aggregator
from app.services.kpi_calculator import KPICalculator

logger = logging.getLogger(__name__)


class KPIPipeline:
    """KPI 산출 전체 파이프라인"""

    def __init__(self, kdrg_file_path: str | None = None):
        """
        초기화

        Args:
            kdrg_file_path: KDRG 버전4.4_질병군명칭_20221101(변동없음).xlsx 파일 경로
        """
        self.file_parser = FileParser()
        self.period_classifier = PeriodClassifier()
        self.kdrg_file_path = kdrg_file_path
        self.kdrg_matcher = None  # run_pipeline에서 초기화
        self.aggregator = Aggregator()
        self.kpi_calculator = KPICalculator()

    def run_pipeline(
        self,
        hira_file_path: str,
        smc_file_path: str,
        hospital: str,
        filter_quarter: int | None = None
    ) -> Dict:
        """
        전체 파이프라인 실행

        Returns:
            {
                'summary_kpi': {...},
                'doctor_kpis_off_season': DataFrame,
                'doctor_kpis_normal': DataFrame,
                'disease_kpis_off_season': DataFrame,
                'disease_kpis_normal': DataFrame,
                'department_kpis_off_season': DataFrame,
                'department_kpis_normal': DataFrame,
                'insights_off_season': [...],
                'insights_normal': [...],
                'metadata': {...}
            }
        """
        logger.info(f"KPI 파이프라인 시작: {hospital}")

        # 1. 파일 파싱
        logger.info("1. 파일 파싱 시작")
        hira_df = self.file_parser.parse_hira_file(hira_file_path)
        smc_df = self.file_parser.parse_smc_file(smc_file_path, filter_quarter=filter_quarter)

        # 병원 필터링
        smc_df = smc_df[smc_df['hospital'] == hospital].copy()

        quarter_info = f" (Q{filter_quarter})" if filter_quarter else " (전체)"
        logger.info(f"HIRA: {len(hira_df)}건, SMC({hospital}){quarter_info}: {len(smc_df)}건")

        # 2. 데이터 검증
        logger.info("2. 데이터 검증")
        is_valid, validation_msg = self.file_parser.validate_files(hira_df, smc_df)
        if not is_valid:
            raise ValueError(f"데이터 검증 실패: {validation_msg}")

        # 3. 기간 분류
        logger.info("3. 기간 분류")
        smc_df = self.period_classifier.classify_dataframe(smc_df)

        off_season_count = len(smc_df[smc_df['period'] == 'off_season'])
        normal_count = len(smc_df[smc_df['period'] == 'normal'])
        logger.info(f"비수기: {off_season_count}건, 통상기간: {normal_count}건")

        # 4. KDRG 4.4 매칭 (ICD-10 기반 + 진단명 기반)
        logger.info("4. KDRG 4.4 ICD-10 기반 DRG 매칭")

        # KDRG Matcher 초기화
        self.kdrg_matcher = KDRGMatcher()

        # KDRG 4.4 테이블 로드
        if self.kdrg_file_path:
            self.kdrg_matcher.load_kdrg_table(self.kdrg_file_path)
            logger.info(f"KDRG 4.4 로드 완료: {self.kdrg_file_path}")

        # ICD-10 매핑 파일 로드 (최우선)
        from app.config import PROJECT_ROOT
        icd10_mapping_file = PROJECT_ROOT / "data" / "mapping" / "icd10_to_adrg_from_kdrg46.xlsx"
        if icd10_mapping_file.exists():
            self.kdrg_matcher.load_icd10_mapping(icd10_mapping_file)
            logger.info(f"ICD-10 매핑 로드 완료: {icd10_mapping_file}")
        else:
            logger.warning(f"ICD-10 매핑 파일 없음: {icd10_mapping_file}")

        # 수동 진단명 매핑 파일 로드 (폴백) - 병원별 분리
        # 대전: 주상병 매핑 제외, 유성: 주상병 매핑 포함
        if hospital == "유성":
            mapping_file = PROJECT_ROOT / "data" / "mapping" / "diagnosis_kdrg44_mapping_유성.xlsx"
        else:  # 대전
            mapping_file = PROJECT_ROOT / "data" / "mapping" / "diagnosis_kdrg44_mapping_대전.xlsx"

        if mapping_file.exists():
            self.kdrg_matcher.load_manual_mapping(mapping_file)
            logger.info(f"진단명 수동 매핑 로드 완료 ({hospital}): {mapping_file.name}")
        else:
            logger.warning(f"진단명 매핑 파일 없음: {mapping_file}")

        # ICD-10 코드 추가 (병원별 시트에서)
        from app.services.hospital_summary_parser import HospitalSummaryParser
        hospital_summary_df = HospitalSummaryParser.parse_hospital_summary(
            PROJECT_ROOT / 'data' / 'smc' / '25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx'
        )
        diagnosis_to_icd10 = dict(zip(
            hospital_summary_df['diagnosis'],
            hospital_summary_df['icd10_code']
        ))
        smc_df['icd10_code'] = smc_df['diagnosis'].map(diagnosis_to_icd10)

        icd10_coverage = smc_df['icd10_code'].notna().sum()
        logger.info(f"ICD-10 커버리지: {icd10_coverage}/{len(smc_df)} ({icd10_coverage/len(smc_df)*100:.1f}%)")

        # ICD-10 + 진단명 기반 매칭
        smc_df, disease_target_map = self.kdrg_matcher.match_smc_to_hira(smc_df, hira_df)

        matched_count = sum(1 for d in smc_df['diagnosis'].unique() if d in disease_target_map)
        total_diagnoses = len(smc_df['diagnosis'].unique())
        match_rate = (matched_count / total_diagnoses) * 100 if total_diagnoses > 0 else 0
        logger.info(f"진단명 매칭률: {match_rate:.1f}% ({matched_count}/{total_diagnoses}개 진단명)")

        # SMC 데이터에 target_los 추가
        smc_df['target_los'] = smc_df['diagnosis'].map(disease_target_map)

        # 5. 질환별/의료진별/진료과별 집계 (기간별로 분리)
        logger.info("5. 데이터 집계 (기간별)")

        # 비수기
        disease_kpis_off = self._aggregate_and_calculate(
            smc_df, hospital, 'off_season'
        )

        # 통상기간
        disease_kpis_normal = self._aggregate_and_calculate(
            smc_df, hospital, 'normal'
        )

        # 6. 요약 KPI 생성 (기간별)
        logger.info("6. 요약 KPI 생성")
        summary_kpi_off = self._calculate_summary_kpi_for_period(
            disease_kpis_off['doctor_kpis'],
            hospital,
            'off_season'
        )
        summary_kpi_normal = self._calculate_summary_kpi_for_period(
            disease_kpis_normal['doctor_kpis'],
            hospital,
            'normal'
        )

        # 7. 인사이트 생성
        logger.info("7. 인사이트 생성")
        insights_off = self._generate_insights(
            disease_kpis_off['disease_kpis'],
            disease_kpis_off['doctor_kpis']
        )
        insights_normal = self._generate_insights(
            disease_kpis_normal['disease_kpis'],
            disease_kpis_normal['doctor_kpis']
        )

        logger.info("KPI 파이프라인 완료")

        return {
            'summary_kpi_off_season': summary_kpi_off,
            'summary_kpi_normal': summary_kpi_normal,
            'doctor_kpis_off_season': disease_kpis_off['doctor_kpis'],
            'doctor_kpis_normal': disease_kpis_normal['doctor_kpis'],
            'disease_kpis_off_season': disease_kpis_off['disease_kpis'],
            'disease_kpis_normal': disease_kpis_normal['disease_kpis'],
            'department_kpis_off_season': disease_kpis_off['department_kpis'],
            'department_kpis_normal': disease_kpis_normal['department_kpis'],
            'insights_off_season': insights_off,
            'insights_normal': insights_normal,
            'metadata': {
                'hira_count': len(hira_df),
                'smc_count': len(smc_df),
                'total_patients': len(smc_df),
                'off_season_patients': off_season_count,
                'normal_patients': normal_count,
                'off_season_count': off_season_count,
                'normal_count': normal_count,
                'match_rate': match_rate,
                'matched_patients': matched_count
            }
        }

    def _aggregate_and_calculate(
        self,
        smc_df: pd.DataFrame,
        hospital: str,
        period: str
    ) -> Dict:
        """기간별 집계 및 KPI 계산"""

        # 해당 기간 데이터만 필터링
        period_df = smc_df[smc_df['period'] == period].copy()

        if len(period_df) == 0:
            logger.warning(f"{period} 데이터가 없습니다")
            return {
                'disease_kpis': pd.DataFrame(),
                'doctor_kpis': pd.DataFrame(),
                'department_kpis': pd.DataFrame()
            }

        # 환자수 6명 미만 질환 필터링
        # - 전체 disease_target_map 먼저 생성 (모든 질환 포함)
        # - 질환별 KPI 표시: 6명 이상 질환만 (통계적 유의성)
        # - 의료진/진료과 KPI: 모든 질환 포함 (실제 성과 반영)
        from app.config import settings

        # 전체 질환 집계 (disease_target_map 생성용)
        all_disease_agg = self.aggregator.aggregate_by_disease(
            period_df, hospital, period
        )

        # 전체 질환 KPI 계산 (disease_target_map 생성용)
        all_disease_kpi_dicts = all_disease_agg.apply(
            self.kpi_calculator.calculate_disease_kpi, axis=1
        ).tolist()
        all_disease_kpis = pd.DataFrame(all_disease_kpi_dicts)

        # disease_target_map 생성 (모든 질환 포함, NaN만 제거)
        disease_target_map = {
            diagnosis: target_los
            for diagnosis, target_los in zip(all_disease_kpis['diagnosis'], all_disease_kpis['target_los'])
            if pd.notna(target_los)
        }
        logger.info(f"  → {len(disease_target_map)}개 진단명에 목표 LOS 설정됨 (전체)")

        # 6명 이상 질환만 필터링 (표시용)
        disease_kpis = all_disease_kpis[all_disease_kpis['patient_count'] >= settings.MIN_PATIENT_COUNT].copy()
        filtered_count = len(all_disease_kpis) - len(disease_kpis)
        logger.info(f"  → 환자수 {settings.MIN_PATIENT_COUNT}명 미만 질환 {filtered_count}개 제외 (질환별 KPI 표시에서만)")

        # 의료진별 집계 및 KPI 계산 (전체 데이터 사용 - 모든 환자 성과 반영)
        doctor_disease_df = self.aggregator.aggregate_by_doctor_disease(period_df, hospital, period)
        doctor_agg = self.aggregator.aggregate_by_doctor(
            period_df, hospital, period
        )

        # 의료진별 KPI 계산 (가중 평균 목표 LOS)
        doctor_kpi_dicts = doctor_agg.apply(
            lambda row: self.kpi_calculator.calculate_doctor_kpi(
                row, disease_target_map, doctor_disease_df
            ), axis=1
        ).tolist()
        doctor_kpis = pd.DataFrame(doctor_kpi_dicts)

        # 진료과별 집계 및 KPI 계산 (필터링 전 데이터 사용)
        department_agg = self.aggregator.aggregate_by_department(
            period_df, hospital, period
        )

        # 진료과별 KPI 계산
        department_kpi_dicts = department_agg.apply(
            lambda row: self.kpi_calculator.calculate_department_kpi(
                row, disease_target_map, doctor_disease_df
            ), axis=1
        ).tolist()
        department_kpis = pd.DataFrame(department_kpi_dicts)

        return {
            'disease_kpis': disease_kpis,
            'doctor_kpis': doctor_kpis,
            'department_kpis': department_kpis
        }

    def _calculate_summary_kpi_for_period(
        self,
        doctor_kpis: pd.DataFrame,
        hospital: str,
        period: str
    ) -> Dict:
        """기간별 요약 KPI 계산"""

        if len(doctor_kpis) > 0:
            valid_doctors = doctor_kpis[doctor_kpis['status'] == 'calculated']

            # 단순 평균 재원일수 (환자수 가중치 없이)
            simple_avg_current_los = valid_doctors['current_los'].mean() if len(valid_doctors) > 0 else 0
            simple_avg_target_los = valid_doctors['target_los'].mean() if len(valid_doctors) > 0 else 0

            total_additional_bed_days = valid_doctors['additional_bed_days'].sum() if len(valid_doctors) > 0 else 0
            patient_count = doctor_kpis['patient_count'].sum()

            # 가동률 계산
            bed_count = 300 if hospital == "대전" else 250
            period_days = 122 if period == 'off_season' else 243  # 비수기 122일, 통상기간 243일
            total_bed_days = doctor_kpis['total_bed_days'].sum()
            available_bed_days = bed_count * period_days

            current_utilization_rate = (total_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0
            target_bed_days = total_bed_days + total_additional_bed_days
            target_utilization_rate = (target_bed_days / available_bed_days) * 100 if available_bed_days > 0 else 0
        else:
            simple_avg_current_los = 0
            simple_avg_target_los = 0
            total_additional_bed_days = 0
            patient_count = 0
            current_utilization_rate = 0
            target_utilization_rate = 0

        return {
            'simple_avg_current_los': simple_avg_current_los,
            'simple_avg_target_los': simple_avg_target_los,
            'total_additional_bed_days': total_additional_bed_days,
            'current_utilization_rate': current_utilization_rate,
            'target_utilization_rate': target_utilization_rate,
            'patient_count': patient_count
        }

    def _generate_insights(
        self,
        disease_kpis: pd.DataFrame,
        doctor_kpis: pd.DataFrame
    ) -> List[str]:
        """인사이트 생성"""
        insights = []

        if len(disease_kpis) > 0:
            valid_diseases = disease_kpis[disease_kpis['status'] == 'calculated'].copy()
            if len(valid_diseases) > 0:
                valid_diseases['los_gap'] = pd.to_numeric(valid_diseases['los_gap'])
                # 가장 어려운 질환
                hardest_disease = valid_diseases.nlargest(1, 'los_gap')
                if len(hardest_disease) > 0:
                    disease_name = hardest_disease.iloc[0]['diagnosis']
                    los_gap = hardest_disease.iloc[0]['los_gap']
                    insights.append(
                        f"목표 도달이 가장 어려운 질환: {disease_name} (+{los_gap:.1f}일)"
                    )

        if len(doctor_kpis) > 0:
            valid_doctors = doctor_kpis[doctor_kpis['status'] == 'calculated'].copy()
            if len(valid_doctors) > 0:
                valid_doctors['additional_bed_days'] = pd.to_numeric(valid_doctors['additional_bed_days'])
                valid_doctors['los_gap'] = pd.to_numeric(valid_doctors['los_gap'])
                
                # 임팩트 상위 의료진 TOP 3
                top3_doctors = valid_doctors.nlargest(3, 'additional_bed_days')
                total_impact = top3_doctors['additional_bed_days'].sum()
                insights.append(
                    f"임팩트 상위 의료진 TOP3 합산 추가 병상일수: {total_impact:,.0f}일"
                )

                # 전체 평균 조정 필요량
                avg_gap = valid_doctors['los_gap'].mean()
                insights.append(
                    f"기준치 대비 전체 평균 조정 필요량: {avg_gap:+.1f}일"
                )

        return insights
