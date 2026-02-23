# 진단명 기반 DRG 매칭 완료 및 대시보드 배포 준비

**작업 일자:** 2026-02-22
**프로젝트:** 선메디컬센터 병상가동 KPI 산출 프로그램

---

## ✅ 완료된 작업

### 1. **진단명 기반 DRG 매칭으로 전환**

**문제 발견:**
- SMC 데이터에 ICD-10 코드(질병코드)가 존재하지 않음
- 이전 ICD-10 기반 매칭은 작동하지 않았음 (데이터 없음)

**해결 방법:**
- `drg_matcher.py` 전면 재작성 → 진단명 기반 매칭
- HIRA ADRG명과 SMC 진단명 직접 매칭
- 수동 매핑 테이블 생성 및 로드 기능 추가

### 2. **수동 매핑 테이블 생성**

**파일 위치:** `/data/mapping/diagnosis_drg_mapping.xlsx`

**매칭 현황:**
- 수동 매핑: 15개 핵심 진단명
- 자동 매칭: 31개 추가 진단명 (부분 일치)
- **총 매칭: 46개 진단명** (환자 커버리지: ~30%)

**주요 매핑 항목:**
```
협심증 → 협심증
급성 충수염 → 복잡한 주진단이 없는 충수절제술
담석증 → 복강경을 이용한 전담낭절제술
상세불명 병원체의 폐렴 → 세균성 폐렴
뇌경색증 → 뇌경색
감염성 및 상세불명 기원의 기타 위장염 및 결장염 → 기타 위장관 출혈
... (총 46개)
```

### 3. **정적 HTML 네비게이션 수정**

**문제:**
- URL 파라미터 방식은 정적 파일에서 작동하지 않음

**해결:**
- 파일 경로 기반 네비게이션으로 변경
- 병원 전환: `../유성/index_off_season.html`
- 기간 전환: `index_normal.html`
- 서브디렉토리 대응: `../../대전/index_off_season.html`

### 4. **KPI 계산 결과**

#### 대전선병원 (비수기 - 11-12월)
- **전체 환자:** 2,557명
- **매칭된 질환:** 41개 (총 324개 진단명 중)
- **데이터가 있는 의료진:** 32명 / 42명 (76%)

**의료진 TOP 6:**
1. 범종욱 (IMC) - 28명, -0.95일
2. 박기용 (PED) - 17명, -1.60일
3. 오현량 (OB) - 10명, -3.28일
4. 김도희 (PED) - 19명, -2.29일
5. 유지만 (GS) - 50명, -0.97일
6. 김원형 (SC) - 9명, -8.93일

**주요 질환:**
1. 담석증 - 50명, 목표 5.49일
2. 장의 기타 질환 - 48명, 목표 5.08일
3. 감염성 및 상세불명 기원의 기타 위장염 및 결장염 - 43명, 목표 4.25일

---

## 📁 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/services/drg_matcher.py` | 진단명 기반 매칭으로 전면 재작성 |
| `app/services/kpi_pipeline.py` | 진단명 매칭 사용, disease_target_map NaN 제거 |
| `generate_static_dashboard.py` | 파일 경로 기반 네비게이션 스크립트 주입 |
| `data/mapping/diagnosis_drg_mapping.xlsx` | 수동 매핑 테이블 생성 (15개 핵심) |

---

## 🚀 배포 준비 완료

### 생성된 정적 HTML
```
docs/
├── index.html                          # 자동 리디렉션
├── 대전/
│   ├── index_off_season.html          # ✅ 데이터 표시됨
│   ├── index_normal.html              # ✅ 데이터 표시됨
│   ├── department_off_season.html
│   ├── department_normal.html
│   ├── doctors_off_season/            # 10명
│   ├── doctors_normal/                # 10명
│   ├── diseases_off_season/           # 10개
│   └── diseases_normal/               # 10개
└── 유성/
    └── (동일 구조)
```

**총 파일 수:** 88개 HTML 파일

### 로컬 실행 방법

```bash
# 방법 1: 파일 더블클릭 (가장 간단)
open /Users/chul/Documents/bed-kpi/docs/index.html

# 방법 2: 웹서버 실행
cd /Users/chul/Documents/bed-kpi/docs
python3 -m http.server 8080
# http://localhost:8080 접속
```

### GitHub Pages 배포

1. **저장소 준비**
```bash
cd /Users/chul/Documents/bed-kpi
git add docs/
git add data/mapping/diagnosis_drg_mapping.xlsx
git add backend/app/services/drg_matcher.py
git add backend/app/services/kpi_pipeline.py
git add generate_static_dashboard.py

git commit -m "$(cat <<'EOF'
진단명 기반 DRG 매칭 적용 및 정적 대시보드 완성

- DRG 매칭 방식 변경: ICD-10 → 진단명 기반
- 46개 진단명 매칭 (수동 15개 + 자동 31개)
- 정적 HTML 네비게이션 수정 (파일 경로 기반)
- 대전/유성 × 비수기/통상기간 총 88개 HTML 생성
- 데이터가 있는 의료진: 32명 (대전 비수기 기준)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

git push origin main
```

2. **GitHub Pages 설정**
   - Repository Settings > Pages
   - Source: `main` branch
   - Folder: `/docs`
   - Save

3. **배포 URL**
   ```
   https://<username>.github.io/<repository>/
   ```

---

## 📊 매칭률 분석

### 진단명 매칭률
- **총 진단명:** 324개
- **매칭된 진단명:** 46개 (14.2%)
- **환자 커버리지:** ~30% (추정)

### 의료진별 매칭률
대부분의 의료진이 10-60% 매칭률을 보임:
- 높음 (60%+): 황시은 (81%), 박기용 (65%), 이연선 (63%)
- 중간 (30-60%): 황시은, 정지윤, 범종욱, 김성숙 등
- 낮음 (<10%): 정윤화 (6.5%), 이철형 (6.0%) 등

---

## 🔧 향후 개선 사항

### 즉시 가능
1. **매핑 테이블 확장**
   - 상위 100개 진단명 매핑 → 환자 커버리지 60%+ 예상
   - 템플릿 파일 활용: `data/mapping/diagnosis_drg_mapping_template.xlsx`

2. **매칭률 50% 이상 목표**
   - 현재 상위 20개 진단명만 매핑해도 40% 달성 가능
   - 주요 질환:
     - 기타 의학적 관리를 위하여 보건서비스와 접하고 있는 사람 (630명)
     - 무릎관절증 (311명)
     - 결장, 직장, 항문 및 항문관의 양성 신생물 (269명)

### 중장기
3. **병원 시스템에서 ICD-10 코드 추출**
   - DRG 청구 데이터에는 ICD-10 코드가 포함되어 있어야 함
   - 청구팀에 ICD-10 코드 포함된 데이터 요청

4. **HIRA 연간 데이터 확보**
   - 현재: 4분기만 (10-12월)
   - 필요: 연간 데이터 → 비수기/통상기간 정확한 KPI 산출

---

## ✅ 검증 체크리스트

- [x] 진단명 기반 매칭 작동 확인 (46개 진단명)
- [x] 의료진 KPI 계산 정상 (32명 데이터 있음)
- [x] 정적 HTML 네비게이션 작동 (파일 경로 기반)
- [x] 대전/유성 병원 전환 가능
- [x] 비수기/통상기간 전환 가능
- [x] 의료진 TOP 6 랭킹 표시
- [x] 진료과/의료진 검색 기능 작동
- [x] 88개 HTML 파일 생성 완료
- [ ] GitHub Pages 배포 (사용자 확인 필요)

---

## 🎯 핵심 성과

1. ✅ **실제 데이터 표시**
   - ICD-10 없이도 진단명 기반으로 매칭 성공
   - 46개 진단명, 32명 의료진 데이터 표시

2. ✅ **서버 없이 실행 가능**
   - 정적 HTML로 변환 완료
   - 파일 더블클릭으로 즉시 실행 가능

3. ✅ **GitHub Pages 배포 준비**
   - docs/ 폴더에 88개 HTML 파일 생성
   - 상대 경로 네비게이션으로 어디서나 작동

4. ✅ **다크 테마 UI**
   - 색상: #292F36, #4ECDC4, #FFFFFF
   - Frosted glass header
   - 반응형 디자인

---

**작성자:** Claude Sonnet 4.5
**최종 업데이트:** 2026-02-22 20:00

**참고 문서:**
- [실행방법.md](실행방법.md) - 사용자 가이드
- [UI_UPDATE_COMPLETE.md](UI_UPDATE_COMPLETE.md) - UI 디자인
- [CLAUDE.md](CLAUDE.md) - 프로젝트 문서
