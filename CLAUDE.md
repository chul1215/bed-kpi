# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

대전선병원·유성선병원 의사별 TOP7 진단 기준, 비수기·통상기간 목표 재원일수를 산출하고 조정 대상을 시각화하는 **HTML 단일 파일 대시보드**.

- **배포**: GitHub Pages — https://chul1215.github.io/bed-kpi/
- **스택**: Vanilla JS + CSS, 외부 라이브러리 없음 (Google Fonts/Material Symbols CDN만)

## 로컬 실행

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

`fetch()`로 `data.js`와 `reports/*.md`를 로드하므로 **`file://` 직접 열기 불가** (CORS). 반드시 HTTP 서버 필요.

배포는 git push → GitHub Actions 없이 Pages 자동 반영 (`.nojekyll` 존재).

---

## 핵심 비즈니스 로직

| 항목 | 대전선병원 | 유성선병원 |
|------|-----------|-----------|
| 허가병상 | 332 | 387 |
| 현재 가동률 | 86.0% | 72.1% |
| 목표 가동률 | 88.3% | 88.3% |
| **조정 방향** | **단축** | **연장** |
| 의사 수 | 43명 | 50명 (FM 제외) |
| 레코드 수 | 255건 | 286건 |

### 기간 구분
- **비수기** (3·4·11·12월, 122일): 가동률 **85%** 목표
- **통상기간** (1·2·5~10월, 243일): 가동률 **90%** 목표

### 필터링 기준
- **의사별** 진단 환자수 **6명 이상**만 포함 — 전체 병원 기준이 아닌, **특정 의사가 해당 진단을 6명 이상 진료**한 경우
- 상위 **7개** 진단 (환자수 기준)
- **FM(가정의학과) 제외** — 대전·유성 모두

### diff 해석 (핵심 로직)
```
diff = 현재재원일수 - 목표재원일수

단축 방향 (대전): diff > 0 → 줄여야 함 (빨강)   → needAdj: diff_off>0.05 || diff_norm>0.05
연장 방향 (유성): diff < 0 → 늘려야 함 (초록)   → needAdj: diff_off<-0.05 || diff_norm<-0.05
```

### 목표 재원일수 산출 공식
```
off_ratio  = (beds × 122 × 0.85) / cur_off_total
norm_ratio = (beds × 243 × 0.90) / cur_norm_total

tgt_off  = cur_off  × off_ratio   (각 레코드 비수기 목표)
tgt_norm = cur_norm × norm_ratio  (각 레코드 통상 목표)

annual_ratio = avail × tgt_occ% / cur_total
tgt_annual   = cur × annual_ratio
```

### vs 심평원 해석
```
vs_hira (저장값) = cur - hira
표시값           = hira - cur  (부호 반전 — 심평원 도달을 위한 변화량)
```

---

## 파일 구조

```
index.html      # UI + 전체 로직 (단일 파일, ~64KB)
data.js         # RAW 데이터 (203KB) — const RAW = { data: {대전,유성}, summary: {대전,유성} }
reports/
├── 대전/       # 43명 KPI 보고서 + 00_총괄요약.md
└── 유성/       # 50명 KPI 보고서 + 00_총괄요약.md
.nojekyll       # GitHub Pages Jekyll 처리 방지
```

### index.html 내부 구조
- `<style>` — CSS 변수 기반 다크 테마 + 모바일 미디어 쿼리 (`≤768px`, `≤480px`)
- `<nav>` — 병원 탭 전환
- `<div#p-dj>` / `<div#p-ys>` — JS로 동적 생성되는 대전/유성 패널
- `<div#doc-modal>` — 의사별 리포트 모달 (단일 인스턴스, innerHTML 덮어쓰기)

### 주요 JS 함수
| 함수 | 역할 |
|------|------|
| `render(h)` | 패널 HTML 생성, `annual_ratio` 계산, `--hosp-color` CSS 변수 주입 |
| `af(h)` | 필터 적용 → `filt[]` 배열 갱신 (의사 선택 / 검색 / 모드) |
| `sw(h)` | 탭 전환 (`curPg=1` 리셋 + `af()` 호출) |
| `sm(h,m)` | 모드 전환 (`'all'`/`'need'`/`'hira'`) |
| `ds(h,c)` | 컬럼 정렬 토글 (null 값은 `sDir>0 ? 9999 : -9999` 치환) |
| `gp(h,p)` | 페이지 이동 — 반드시 `af(h)` 먼저 호출 (병원 교차 오염 방지) |
| `openDoc(h,doctor)` | 의사별 리포트 모달 열기 |
| `buildDocChart(...)` | 모달 내 SVG 바 차트 생성 |
| `dlReport(h,doctor)` | `reports/{병원}/{의사명}_{진료과코드}_KPI분석보고서.md` 다운로드 |
| `dlSummary(h)` | `reports/{병원}/00_총괄요약.md` 다운로드 |
| `exportCSV(h)` | 현재 `filt` 기준 CSV 내보내기 (BOM+UTF-8, Excel 호환) |

---

## 데이터 스키마

### RAW.data[병원명] — 각 레코드
| 필드 | 타입 | 설명 |
|------|------|------|
| `doctor` | string | 의사명 |
| `diag` | string | 진단명 (한국어) |
| `n` / `off_n` / `norm_n` | number | 전체/비수기/통상 환자수 |
| `cur` / `cur_off` / `cur_norm` | number | 전체/비수기/통상 현재 평균 재원일수 |
| `tgt_off` / `tgt_norm` | number | 비수기/통상 목표 재원일수 |
| `diff_off` / `diff_norm` | number | `cur - tgt` (비수기/통상) |
| `hira` | number\|null | 심평원 전국 평균 재원일수 |
| `vs_hira` | number\|null | `cur - hira` (표시 시 부호 반전) |

### RAW.summary[병원명]
| 필드 | 설명 |
|------|------|
| `beds` / `avail` | 허가병상수 / 가용 병상일수 (대전:121,180 / 유성:140,462) |
| `cur_total` | 현재 총 재원일수 (n≥6 필터 적용) |
| `cur_occ` / `tgt_occ` | 현재/목표 가동률 (%) |
| `direction` | `"단축"` \| `"연장"` |
| `doc_dept` | `{의사명: 진료과코드}` — 드롭다운 그룹화 + 보고서 파일명 생성에 사용 |

---

## 테이블 컬럼 구성 (8컬럼)

| # | 컬럼 | 정렬키 |
|---|------|--------|
| 0 | 의사명 | `doctor` |
| 1 | 진단명 | `diag` |
| 2 | 환자수 + 미니바 | `n` |
| 3 | 비수기 목표 85% | `tgt_off` |
| 4 | 통상기간 목표 90% | `tgt_norm` |
| 5 | 연간목표 88.3% | `cur` |
| 6 | 심평원 | `hira` |
| 7 | vs 심평원 | `vs_hira` |

---

## 전역 변수

| 변수 | 용도 |
|------|------|
| `curH` | 현재 활성 병원 (`'대전'` \| `'유성'`) |
| `filt` | 현재 필터링된 레코드 배열 (단일 병원 기준) |
| `sCol` / `sDir` | 정렬 컬럼 인덱스 / 방향 (1=ASC, -1=DESC) |
| `curPg` | 현재 페이지 (PG=25건/페이지) |
| `window['mode_'+h]` | 병원별 모드 (`'all'`/`'need'`/`'hira'`) |
| `window['annual_ratio_'+h]` | 연간 조정비율 — `render()` 시 계산, `renderTbl()`에서 사용 |

---

## CSS 테마

| 용도 | 변수 | 값 |
|------|------|-----|
| 대전 | `--dj` | `#137fec` |
| 유성 | `--ys` | `#10b981` |
| 병원별 동적 | `--hosp-color` | `render()`에서 패널별 주입 |
| 비수기 | `--indigo` | `#818cf8` |
| 통상기간 | `--gold` | `#f59e0b` |
| 줄여야 함 | `--red` | `#fa6238` |
| 늘려야 함 | `--green` | `#0bda5b` |

**모바일 미디어 쿼리**: `≤768px` (태블릿/폰) + `≤480px` (소형 폰). 모달은 768px 이하에서 하단 시트 방식으로 전환.

**DOM ID 규칙**: `sel-대전`, `inp-유성`, `tbody-대전` 등 **한글 ID 사용** — querySelector 시 이스케이프 필요 없음(getElementById 사용).

---

## 개발 시 주의사항

1. **direction 변경 시**: `needAdj` 조건, `pillDiff()` 색상, `diffColor`, `vs_hira` 색상 로직 모두 연동
2. **데이터 갱신**: Python으로 RAW JSON 재생성 후 `data.js` 교체 (`const RAW = {...};` 형태 유지)
3. **심평원 신규 매칭**: `data/hira/입원일수_20260224163001.xlsx`에서 수동 매핑 (현재 548/548 완료)
4. **보고서 파일명**: `{의사명}_{doc_dept코드}_KPI분석보고서.md` — `doc_dept`에 없는 의사는 `{의사명}_KPI분석보고서.md`
5. **totalBedGain**: `Math.abs()` 처리 — 단축/연장 방향 무관하게 양수 표시

### 진료과명 표준 표기 (reports/ MD 파일 기준)
- 치과 → **구강외과**
- 산부인과 → **부인과**
- 순환기내과 → **심장내과**

---

## 데이터 재생성 방법

```python
import pandas as pd, json

filepath = "data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx"
df = pd.read_excel(filepath, sheet_name='Sheet1')

OFF_MONTHS = [3,4,11,12]
config = {
    '대전': {'beds':332, 'avail':121180},
    '유성': {'beds':387, 'avail':140462},
}

for hosp, cfg in config.items():
    sub = df[df['구분']==hosp].copy()
    sub['퇴원일자'] = pd.to_datetime(sub['퇴원일자'])
    sub['month'] = sub['퇴원일자'].dt.month
    sub['의사명'] = sub['의사명'].str.split().str[0]
    sub['period'] = sub['month'].apply(lambda m: 'off' if m in OFF_MONTHS else 'norm')
    sub = sub[sub['퇴원과'] != 'FM']  # FM 제외
    sub_f = sub.groupby(['의사명','진단명'], group_keys=False).filter(lambda x: len(x)>=6)

    BEDS=cfg['beds']; AVAIL=cfg['avail']
    off_total  = sub_f[sub_f['period']=='off']['평균재원'].sum()
    norm_total = sub_f[sub_f['period']=='norm']['평균재원'].sum()
    off_ratio  = (BEDS*122*0.85) / off_total
    norm_ratio = (BEDS*243*0.90) / norm_total
    # 의사별 TOP7 레코드 생성 ...
```

원본 소스: `data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx` (Sheet1, 33,853건, 2025 FY)
