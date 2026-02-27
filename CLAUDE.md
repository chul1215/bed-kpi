# CLAUDE.md — 의사별 TOP7 목표재원일수 대시보드

## 프로젝트 개요

대전선병원·유성선병원 의사별 TOP7 진단 기준, 비수기·통상기간 목표 재원일수를 산출하고 조정 대상을 시각화하는 **HTML 대시보드**.

- **배포**: GitHub Pages — https://chul1215.github.io/bed-kpi/

## 핵심 비즈니스 로직

| 항목 | 대전선병원 | 유성선병원 |
|------|-----------|-----------|
| 허가병상 | 332 | 387 |
| 현재 가동률 | 82.0% | 72.1% |
| 목표 가동률 | 88.3% | 88.3% |
| **조정 방향** | **연장** (미달 → 늘려야) | **연장** (미달 → 늘려야) |
| 의사 수 | 43명 | 50명 (FM 제외) |
| 레코드 수 | 255건 | 286건 |

### 기간 구분 & 목표
- **비수기** (3·4·11·12월, 122일): 가동률 **85%** 달성 목표
- **통상기간** (1·2·5~10월, 243일): 가동률 **90%** 달성 목표

### 필터링 기준
- **의사별** 진단 환자수 **6명 이상**만 포함 (전체 진단 기준 아님)
- 상위 **7개** 진단 (환자수 기준)
- **FM(가정의학과) 제외** — 대전·유성 모두
- 0.5일 미만 제외 조건 **없음** (전체 진단 표시)

### 데이터 기준 — 의사별 진단 n≥6 필터 (bedsimulator 기준)

유성선병원 bedsimulator 기준:
- 필터: **의사별 진단 환자수 ≥ 6명**
- 대전: 99,377일 / 121,180일 = **82.0%**
- 유성: 102,883일 / 140,462일 = **72.1%** (FM 제외 후)

> **주의**: 진단 전체 환자수 n≥6(전체 병원 기준)이 아닌, **특정 의사가 해당 진단을 6명 이상 진료한 경우**만 포함

### diff 해석 (가장 중요한 로직)
```
diff = 현재재원일수 - 목표재원일수

두 병원 모두 연장 방향:
  diff < 0 → 늘려야 함 (초록색 +표시)  → needAdj: diff_off<-0.05 || diff_norm<-0.05
```

### 목표 재원일수 산출 공식
```
avail_off  = beds × off_days         (비수기 가용 병상일수)
avail_norm = beds × norm_days        (통상 가용 병상일수)
tgt_off_total  = avail_off  × 0.85   (비수기 목표 총재원일수)
tgt_norm_total = avail_norm × 0.90   (통상 목표 총재원일수)

off_ratio  = tgt_off_total  / cur_off_total   (비수기 조정비율)
norm_ratio = tgt_norm_total / cur_norm_total  (통상 조정비율)

각 레코드:
  tgt_off  = cur_off  × off_ratio    (비수기 목표)
  tgt_norm = cur_norm × norm_ratio   (통상 목표)

연간목표:
  annual_ratio = avail × tgt_occ% / cur_total
  tgt_annual   = cur × annual_ratio
  diff_annual  = cur - tgt_annual
```

### vs 심평원 해석
```
vs_hira (저장값) = cur - hira   (병원 - 심평원)
표시값           = hira - cur   (심평원 도달을 위한 변화량, 부호 반전)

표시값 > 0: 재원일수를 늘려야 심평원 수준 도달
표시값 < 0: 재원일수를 줄여야 심평원 수준 도달
```

---

## 파일 구조

```
index.html            # UI + 로직 (24KB)
├── <style>           # CSS 변수 기반 다크 테마
│   └── 색상 변수: --dj(파랑), --ys(초록), --bg, --card 등
├── <nav>             # 병원 탭 전환 (대전/유성)
├── <div#p-dj>        # 대전 패널 (JS 동적 생성)
├── <div#p-ys>        # 유성 패널 (JS 동적 생성)
├── <script src="data.js">  # 외부 데이터 로드
└── <script>          # 전체 로직
    ├── sw()          # 병원 탭 전환 (curPg 리셋 + af() 호출)
    ├── render()      # 패널 HTML 생성 (요약카드 + 필터 + 테이블)
    │   └── annual_ratio 계산 → window['annual_ratio_'+h] 저장
    ├── sm()          # 모드 전환 (전체/조정필요/심평원有)
    ├── af()          # 필터 적용 (의사/검색/모드 → filt 배열)
    ├── renderTbl()   # 테이블 렌더링 (25건 페이지네이션, 8컬럼)
    ├── pillDiff()    # 차이 pill 뱃지 렌더링
    ├── renderPagi()  # 페이지네이션 UI
    ├── gp()          # 페이지 이동 (af() 선호출 후 페이지 이동)
    └── ds()          # 컬럼 정렬 토글 (ASC/DESC)

data.js               # RAW 데이터 (203KB, 별도 분리)
├── RAW.data.대전[]          (255건, 43의사)
├── RAW.data.유성[]          (286건, 50의사, FM제외)
├── RAW.summary.대전         (beds, occ, direction, doc_dept 등)
└── RAW.summary.유성
```

---

## 데이터 스키마

### RAW.data[병원명] — 각 레코드

| 필드 | 타입 | 설명 |
|------|------|------|
| `doctor` | string | 의사명 |
| `diag` | string | 진단명 (한국어) |
| `n` | number | 총 환자수 |
| `cur` | number | 현재 평균 재원일수 (전체) |
| `cur_off` | number | 비수기 현재 평균 재원일수 |
| `cur_norm` | number | 통상기간 현재 평균 재원일수 |
| `tgt_off` | number | 비수기 목표 재원일수 |
| `tgt_norm` | number | 통상기간 목표 재원일수 |
| `diff_off` | number | 비수기 차이 (cur_off − tgt_off) |
| `diff_norm` | number | 통상 차이 (cur_norm − tgt_norm) |
| `off_n` | number | 비수기 환자수 |
| `norm_n` | number | 통상 환자수 |
| `hira` | number\|null | 심평원 전국 평균 재원일수 |
| `vs_hira` | number\|null | cur − hira (저장값, 표시 시 부호 반전) |

### RAW.summary[병원명]

| 필드 | 설명 |
|------|------|
| `beds` | 허가병상수 |
| `cur_total` | 현재 총 재원일수 (의사별 n≥6 필터 적용) |
| `avail` | 가용 병상일수 (대전: 121,180 / 유성: 140,462) |
| `cur_occ` / `tgt_occ` | 현재/목표 가동률 (%) |
| `off_months` / `norm_months` | 비수기/통상 월 배열 |
| `off_days` / `norm_days` | 비수기/통상 일수 |
| `cur_off_avg` / `cur_norm_avg` | 비수기/통상 현재 평균 재원일수 |
| `tgt_off_avg` / `tgt_norm_avg` | 비수기/통상 목표 평균 재원일수 |
| `n_off` / `n_norm` | 비수기/통상 총 환자수 |
| `direction` | `"단축"` \| `"연장"` |
| `doc_dept` | `{의사명: 진료과코드}` 딕셔너리 (드롭다운 그룹화용) |

---

## 원본 데이터

- **소스 파일**: `data/smc/25년도 대전, 유성 의사별 퇴원진단(26.01.28_방하나).xlsx`
- **Sheet1**: 건별 퇴원 데이터 (33,853건) — 대전 15,514건, 유성 18,339건
  - 컬럼: 구분, 퇴원일자, 성별, 입원일자, 평균재원, 퇴원과, 진단명, 의사명
- **HIRA 파일**: `data/hira/입원일수_20260224163001.xlsx`
  - 컬럼: 상병코드, 4단상병기호(주상병), 상병명, 평균재원일수
  - 548건 전체 매칭 완료 (직접일치 + 부분일치 + ICD-10 수동매핑)
- 기간: 2025.01.01 ~ 2025.12.31

---

## 테이블 컬럼 구성 (8컬럼)

| # | 컬럼명 | 내용 | 정렬키 |
|---|--------|------|--------|
| 0 | 의사명 | doctor | doctor |
| 1 | 진단명 | diag | diag |
| 2 | 환자수 | n + 바 차트 | n |
| 3 | 비수기 목표 (85%) | cur_off → tgt_off + pill | tgt_off |
| 4 | 통상기간 목표 (90%) | cur_norm → tgt_norm + pill | tgt_norm |
| 5 | 연간목표 (88.3%) | cur → tgt_annual + pill | cur |
| 6 | 심평원 | hira | hira |
| 7 | vs 심평원 | hira−cur (심평원 도달 변화량) | vs_hira |

---

## 전역 변수

| 변수 | 용도 |
|------|------|
| `curH` | 현재 활성 병원 (`'대전'` \| `'유성'`) |
| `sCol` | 정렬 중인 컬럼 인덱스 (null=미정렬) |
| `sDir` | 정렬 방향 (1=ASC, -1=DESC) |
| `curPg` | 현재 페이지 번호 |
| `filt` | 필터링된 레코드 배열 |
| `PG` | 페이지당 행 수 (25) |
| `window['mode_'+h]` | 병원별 현재 모드 (`'all'`/`'need'`/`'hira'`) |
| `window['annual_ratio_'+h]` | 병원별 연간 조정비율 (render() 시 계산) |

---

## CSS 테마

| 용도 | 변수 | 값 |
|------|------|-----|
| 대전 테마 | `--dj` | `#3b82f6` (파랑) |
| 유성 테마 | `--ys` | `#10b981` (초록) |
| 비수기 | `--indigo` | `#818cf8` |
| 통상기간 | `--gold` | `#f59e0b` |
| 줄여야 함 | `--red` | `#f87171` |
| 늘려야 함 | `--green` | `#34d399` |
| 배경 | `--bg` | `#07090f` |
| 카드 | `--card` | `#0e1118` |

DOM ID 규칙: `sel-대전`, `inp-유성`, `tbody-대전` 등 **한글 사용** 주의

---

## 개발 시 주의사항

1. **데이터 갱신**: Python 스크립트로 RAW JSON 재생성 → `data.js` 파일 교체 (`const RAW = {...};` 형태)
2. **direction**: 현재 두 병원 모두 `연장`. 방향 바뀌면 needAdj, pill 색상, vs_hira 색상 로직 모두 영향
3. **심평원 매칭**: 548/548건 완료. 신규 진단 추가 시 `data/hira/입원일수_20260224163001.xlsx`에서 수동 매핑
4. **null 정렬 처리**: `sDir>0 ? 9999 : -9999`로 치환
5. **외부 의존성 없음**: CDN, 라이브러리 미사용. 순수 Vanilla JS + data.js
6. **데이터 분리**: RAW 데이터는 `data.js`로 분리 (GitHub 렌더링 제한 대응, index.html 161KB→24KB)
6. **gp() 버그 수정됨**: 페이지 이동 시 af(h) 선호출로 병원 교차 오염 방지
7. **sw() 버그 수정됨**: 탭 전환 시 curPg=1 리셋 + af(h) 호출

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

    # FM 제외
    sub = sub[sub['퇴원과'] != 'FM']

    # 의사별 진단 n>=6 필터
    sub_f = sub.groupby(['의사명','진단명'], group_keys=False).filter(lambda x: len(x)>=6)

    BEDS=cfg['beds']; AVAIL=cfg['avail']
    off_total  = sub_f[sub_f['period']=='off']['평균재원'].sum()
    norm_total = sub_f[sub_f['period']=='norm']['평균재원'].sum()
    off_ratio  = (BEDS*122*0.85) / off_total
    norm_ratio = (BEDS*243*0.90) / norm_total

    # 의사별 TOP7 레코드 생성 ...
```

---

## 확장 포인트

- [x] ~~데이터를 외부 파일로 분리~~ — data.js로 분리 완료
- [ ] 라이트 모드 지원
- [ ] CSV/Excel 내보내기
- [ ] 의사별 상세 드릴다운 (시계열 차트)
- [x] ~~심평원 매칭률 개선~~ — 548/548건 완료 (ICD-10 수동매핑)
- [x] ~~0.5일 필터 제거~~ — 전체 진단 표시
- [x] ~~연간목표(88.3%) 컬럼 추가~~ — 완료
- [x] ~~진료과별 드롭다운 그룹화~~ — 완료
- [ ] 모바일 반응형 테이블 (현재 min-width:900px)
- [ ] 인쇄 최적화 CSS
- [ ] 진단코드(ICD-10) 컬럼 추가

---

## 실행

```bash
open index.html
# 또는
python3 -m http.server 8000  # http://localhost:8000
# GitHub Pages: https://chul1215.github.io/bed-kpi/
```
