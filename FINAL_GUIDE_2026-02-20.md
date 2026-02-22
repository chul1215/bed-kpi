# 선메디컬센터 병상가동 KPI 시스템 - 최종 가이드

**프로젝트**: 선메디컬센터 시기별 병상가동 KPI 산출 시스템
**완료일**: 2026년 2월 20일
**버전**: v1.0 (정적 HTML 대시보드)
**상태**: 🟡 DRG 매칭 이슈 해결 대기

---

## 🎯 Quick Start

### 1. 대시보드 확인 (즉시 가능)

\`\`\`bash
# 방법 1: 파일 직접 열기 (추천)
open /Users/chul/Documents/bed-kpi/docs/index.html

# 방법 2: 웹서버 사용
cd /Users/chul/Documents/bed-kpi/docs
python3 -m http.server 8080
# http://localhost:8080 접속
\`\`\`

### 2. 데이터 업데이트 시

\`\`\`bash
# 1. data/ 폴더에 새 파일 복사
cp [새_HIRA_파일] data/hira/
cp [새_SMC_파일] data/smc/

# 2. config.py 경로 업데이트
# backend/app/config.py 파일에서 파일명 수정

# 3. HTML 재생성
python3 generate_static_dashboard.py

# 4. docs/ 폴더 확인
open docs/index.html
\`\`\`

---

## 🔴 중요: DRG 매칭 문제

### 현재 상황
- **매칭률**: 2.1% (14개 / 663개 진단명)
- **환자 커버율**: 2.8% (963명 / 33,853명)
- **영향**: KPI 핵심 지표 계산 불가 (NaN 표시)

### 해결 필요
**즉시**: 병원 의무기록팀 미팅
- SMC 데이터에 DRG 코드 추가 가능 여부 확인
- 또는 수동 매핑 작업 진행 (상위 100개 진단명)

자세한 내용: \`DRG_MATCHING_ISSUE_REPORT.md\` 참조

---

## 📖 주요 문서

1. **DRG_MATCHING_ISSUE_REPORT.md** - 문제 상세 분석
2. **plan/개발노트_2026-02-20.md** - 오늘의 모든 작업 기록
3. **CLAUDE.md** - 프로젝트 전체 가이드
4. **plan/PRD.md**, **plan/기획안.md**, **plan/와이어프레임.md** - 업데이트됨

---

**다음 단계**: 병원 의무기록팀 미팅 → 해결 방안 선택 → 실행
