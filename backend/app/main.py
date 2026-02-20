"""
FastAPI 애플리케이션 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import pandas as pd

from app.config import settings
from app.services.dashboard_generator import DashboardGenerator

# 업로드 디렉토리 생성
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="선메디컬센터 병상가동 KPI 산출 프로그램 API",
    debug=settings.DEBUG
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 대시보드 생성기
dashboard_gen = DashboardGenerator()


@app.get("/", response_class=HTMLResponse)
async def home(hospital: str = "대전", period: str = "off_season"):
    """홈 화면"""
    # 샘플 데이터
    summary_kpi = {
        "average_los_gap": 1.8,
        "total_additional_bed_days": 2834,
        "current_utilization_rate": 72.5,
        "target_utilization_rate": 83.1,
        "patient_count": 5186
    }

    doctor_kpis = pd.DataFrame({
        "doctor": ["홍길동", "이순신", "강감찬", "김유신", "이순신2", "홍길동2"],
        "department": ["내과", "정형외과", "신경과", "외과", "소아과", "산부인과"],
        "patient_count": [420, 380, 350, 320, 280, 250],
        "los_gap": [2.1, 1.8, -1.3, 1.5, 2.0, 0.9],
        "additional_bed_days": [882, 684, -455, 480, 560, 225]
    })

    insights = [
        "비수기 기준 목표 도달이 가장 어려운 질환: 폐렴 (+3.0일)",
        "임팩트 상위 의료진 TOP3 합산 추가 병상일수: 3,220일",
        "기준치 대비 전체 평균 조정 필요량: ±1.8일"
    ]

    html = dashboard_gen.render_home(summary_kpi, doctor_kpis, insights, hospital, period)
    return html


@app.get("/department", response_class=HTMLResponse)
async def department(hospital: str = "대전", period: str = "off_season"):
    """진료과 뷰"""
    department_kpis = pd.DataFrame({
        "department": ["내과", "정형외과", "신경과", "외과", "소아과", "산부인과"],
        "patient_count": [1200, 800, 600, 500, 450, 400],
        "current_los": [8.2, 7.0, 9.1, 8.5, 7.8, 8.3],
        "target_los": [9.5, 8.8, 10.0, 9.8, 9.0, 9.5],
        "los_gap": [1.3, 1.8, 0.9, 1.3, 1.2, 1.2],
        "additional_bed_days": [1560, 1440, 540, 650, 540, 480]
    })

    doctor_kpis_by_dept = {
        "내과": pd.DataFrame({
            "doctor": ["홍길동", "이순신"],
            "patient_count": [420, 380],
            "current_los": [7.8, 8.5],
            "los_gap": [1.7, 1.0],
            "additional_bed_days": [714, 380]
        }),
        "정형외과": pd.DataFrame({
            "doctor": ["강감찬", "김유신"],
            "patient_count": [350, 320],
            "current_los": [6.9, 7.2],
            "los_gap": [1.9, 1.6],
            "additional_bed_days": [665, 512]
        })
    }

    html = dashboard_gen.render_department(department_kpis, doctor_kpis_by_dept, hospital, period)
    return html


@app.get("/doctor", response_class=HTMLResponse)
async def doctor(name: str = "홍길동", hospital: str = "대전", period: str = "off_season"):
    """의료진 상세 뷰"""
    doctor_kpi = {
        "patient_count": 420,
        "los_gap": 1.7,
        "additional_bed_days": 714,
        "total_bed_days": 3276,
        "target_los": 9.5,
        "department": "내과"
    }

    disease_kpis = pd.DataFrame({
        "diagnosis": ["폐렴", "당뇨합병증", "심부전", "뇌경색", "고혈압"],
        "patient_count": [120, 95, 80, 70, 55],
        "current_los": [8.0, 7.5, 9.2, 8.8, 7.2],
        "target_los": [10.5, 9.0, 10.0, 10.2, 8.5],
        "los_gap": [2.5, 1.5, 0.8, 1.4, 1.3],
        "additional_bed_days": [300, 143, 64, 98, 72]
    })

    html = dashboard_gen.render_doctor(name, doctor_kpi, disease_kpis, hospital, period)
    return html


@app.get("/disease", response_class=HTMLResponse)
async def disease(name: str = "폐렴", hospital: str = "대전", period: str = "off_season"):
    """질환 뷰"""
    disease_info = {
        "target_los": 10.5,
        "current_los": 8.1,
        "los_gap": 2.4,
        "patient_count": 450
    }

    doctor_distribution = pd.DataFrame({
        "doctor": ["홍길동", "이순신", "강감찬", "김유신"],
        "department": ["내과", "내과", "호흡기내과", "가정의학과"],
        "patient_count": [120, 95, 70, 60],
        "current_los": [8.0, 8.3, 9.0, 7.8],
        "los_gap": [2.5, 2.2, 1.5, 2.7],
        "additional_bed_days": [300, 209, 105, 162]
    })

    html = dashboard_gen.render_disease(name, disease_info, doctor_distribution, hospital, period)
    return html


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


# API 라우터 등록 (추후 추가)
# from app.api import upload, kpi, report, dashboard
# app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
# app.include_router(kpi.router, prefix="/api/kpi", tags=["KPI"])
# app.include_router(report.router, prefix="/api/report", tags=["Report"])
# app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
