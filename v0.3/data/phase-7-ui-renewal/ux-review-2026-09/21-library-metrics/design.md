# Library · 메트릭 브라우저·메트릭 상세·웰니스·Provider 비교 — 개선 설계

**작성일**: 2026-09-27
**대상**: `/v2/library/metrics`, `/v2/library/metrics/:slug`, `/v2/library/wellness`(+ 신규 `/v2/library/wellness/:date`), `/v2/library/providers`(+ 신규 `/v2/library/providers/:group`)
**입력**: 같은 폴더 `data.md`(F-DATA-01~13), `ui.md`(F-UI-01~13), `ux.md`(F-UX-01~15), `00-vision-criteria.md`, `10-today/data.md`(PMC·TRIMP·등급 SSOT 발견), API GET 재조회, DB 읽기 전용 재계산(`mode=ro`)
**공통 규격**: 차트·칩·드릴다운·포맷·로딩·출처 배지·색·타이포는 `10-today/design.md` §C1~C8을 따르고 이 문서에서 재정의하지 않는다. 이 탭에만 필요한 규격은 `§Cn 확장`으로 표시한다. 정합 내역과 남은 충돌은 §11에 있다(2026-09-28 정합).
**결정 반영**: PMC α = `1/τ`(DECISIONS `[P7-UX-REVIEW-0928]` D1). §7.3 C1은 이 결정을 전제로 한다.

---

## 1. 요약

**설계 목표**
1. **숫자를 먼저 바로잡는다.** PMC 시간상수, 사본별 RunPulse 값, Provider 비교 단위, UTRS HRV 척도를 고친 뒤 화면을 고친다. 틀린 수치에 좋은 UI를 입히면 오판만 설득력 있게 전달된다.
2. **값 → 분해 → 원천을 2탭으로 연결한다(P2 D1→D3).** 메트릭 상세의 차트 점을 탭하면 그 날짜의 분해가 인라인으로 열리고, 거기서 원천 활동·웰니스 일자로 한 번 더 이동한다.
3. **표시는 한 곳에서 정한다.** 포맷터 1개(`formatMetric`), 등급 밴드 1벌(서버 레지스트리), 표시 이름 1벌(`metric_labels.py` `MetricLabel` → API `name_ko`·`abbr`, §4.2). 목록·상세·차트·분해·Today가 모두 이 셋을 쓴다.
4. **분해는 결론부터 보여 준다(U6).** "59점 — TSB가 −16점 깎음"을 먼저 쓰고, 그 아래 기여 막대(원시 입력·정규화·가중치·손실)와 공식·버전을 둔다.
5. **Provider 비교는 같은 활동끼리만 비교한다(P3).** 쌍 차이의 중앙값과 n을 보여 주고, 셀을 탭하면 쌍 목록으로 드릴한다.

**범위**: 위 5개 라우트와 공통 컴포넌트(`TrendChart`, `Sparkline`, `MetricBreakdown`→`BreakdownPanel`, `ProviderComparison`, Library 레이아웃), API 6종, RunPulse 계산기 6종(pmc·acwr·utrs·cirs·relative_effort 외 activity-scope 전체, 매트릭스 서비스). 코드는 이 문서에서 수정하지 않는다.

**세 평가 간 상충 판단**

| 쟁점 | 선택 | 이유 |
|---|---|---|
| 분해 표시: 시트(현행, UI 부분 유지안) vs 인라인 패널(UX) | 메트릭 상세는 **인라인 패널**(§C3 확장: 컨테이너만 다르고 본문은 §C3.2 `BreakdownView`). 그 밖의 화면은 D2 패널(§C3.1) | 상세 화면의 과업은 "추세와 원인을 함께 보기"다. 시트는 차트를 가린다(F-UI-04) |
| 등급 밴드: 전환 전 `metricMeaning` 재사용(UI F-UI-06) vs 즉시 제거(DATA F-DATA-02) | **서버 SSOT로 한 번에 전환**(S1), 중간 단계 없음 | 클라이언트 밴드가 이미 오답(TSB −15 "피로 누적")이다. 차트 띠에 옮겨 그리면 오답이 강화된다 |
| 핵심 지표 구성: 현행 CORE 8 고정(UX 고정 기본값) vs 재구성(DATA F-DATA-09) | **DATA 재구성안을 "내 지표" 기본값**으로 하고 사용자 고정(☆)을 허용 | 예측 4개 중복을 없애야 한다. 개인화는 UX안을 수용 |
| 모바일 길이: 카테고리 가로 캐러셀(UX F-UX-15) vs 2열 그리드 통일(UI F-UI-09) | **2열 그리드 + 카테고리당 4장 + "모두 보기 ›"** | 가로 캐러셀은 숨은 카드가 생기고 차트 스크럽 제스처와 충돌한다. 목표 길이 단축(≤1/2)은 달성된다 |
| 예측 헤드라인: `3:40:23`(UX 일관성) vs 범위 표기(DATA) | **§C4 예측 기록 규칙**(신뢰 <0.5: `3:40 (3:26–4:03)` + 신뢰 배지, ≥0.5: `h:mm:ss`)을 목록·상세·Today에 똑같이 적용 | 일관성과 정밀도 문제를 한 포맷으로 함께 해결한다. 신뢰 0.36인 값에 초 단위 정밀도는 거짓 정밀이다 |
| Provider 상세: 메트릭별 비교 화면(UX) vs 쌍 기반 재구축(DATA) | 둘을 결합: `/library/providers/:group` = **쌍 목록 + 겹친 시계열 + 정의 차이** | 쌍 기반이어야 비교 화면이 참이 된다 |

---

## 2. 정보 구조·배치

### 2.1 Library 공통 레이아웃 (F-UX-09, F-UI-13)
`routes/library/+layout.svelte` 신설. 1단 화면은 서브탭, 2단 이상은 같은 높이(48px)의 브레드크럼을 쓴다.
```
1단:  [활동] [메트릭] [웰니스] [소스 비교]            ← 44px 탭, 선택=밑줄 2px
2단:  ‹  Library › 메트릭 › 훈련 준비도        [‹ Today로]  ← from=today일 때만 칩
```

### 2.2 메트릭 브라우저 `/library/metrics`
데스크톱 1280 (사이드바 제외 본문 1016):
```
┌ 서브탭 ───────────────────────────────────────────────────────────┐
│ [🔍 지표 검색 (예: 수면, VO2, 부하)  /]   Provider: [전체][Garmin][RunPulse][Intervals] │
├──────────────┬────────────────────────────────────────────────────┤
│ 카테고리      │ 내 지표 ☆ (8)                     RunPulse 계산 · 기본 │
│ ● 내 지표     │ ┌마라톤 예측──────┐┌Marathon Shape┐┌체력 CTL──┐┌폼 TSB──┐ │
│   오늘 상태   │ │3:40 (3:26–4:03) ││30%  ● 낮음   ││72.7      ││−9 ● 유지│ │
│   훈련 부하   │ │신뢰 낮음 · 14일 ▼6분││30km+ 0회   ││14일 ▲1.2 ││아침 기준│ │
│   레이스 예측 │ └────────────────┘└─────────────┘└──────────┘└────────┘ │
│   능력·효율   │ ┌ACWR 1.06 ●적정┐┌준비도 UTRS 60●보통┐┌HRV 107 ▲평소+35%┐┌안정심박 45┐│
│   수면·회복   │ 오늘 상태 (3) ─────────────────────────── 모두 보기 › │
│   생체 신호   │ ...카드 4장/행, 섹션당 최대 4장...                     │
│   심박 기준값 │                                                    │
│   환경        │ 구성요소 9개는 상위 지표 분해에서 볼 수 있어요.        │
└──────────────┴────────────────────────────────────────────────────┘
```
모바일 390:
```
[활동][메트릭][웰니스][소스 비교]
[🔍 지표 검색                ]
[내 지표][오늘 상태][훈련 부하][레이스…▸   (우측 24px 페이드)
내 지표 ☆                        RunPulse 계산
┌마라톤 예측 ● Garmin?┐┌Marathon Shape┐   ← 2열, 카드 175px
│3:40               ││30%            │
│3:26–4:03 신뢰 낮음 ││● 낮음          │
│~~~~~~~ 14일 ▼6분   ││~~~~~ 14일 ▲0.4 │
└───────────────────┘└───────────────┘
... (4행) ...
훈련 부하 (10)                   모두 보기 ›
[카드][카드] / [카드][카드]
```
**블록 순서 근거**: ① 검색(반복 사용자의 최단 경로) ② 내 지표(매일 보는 4~8개, F-DATA-09·F-UX-08) ③ 의도 기준 카테고리(오늘 상태 → 부하 → 예측 → 능력 → 수면 → 생체 → 심박 기준값 → 환경). 결정 빈도가 높은 순서다. 심박 기준값은 참조값이라 뒤에 둔다.

**카테고리 재편**(F-UX-08, F-DATA-09): `오늘 상태`(UTRS·CIRS·CRS·RRI) / `훈련 부하`(대표 ACWR·TSB·CTL·ATL + 세부 접기: RTTI·LSI·단조로움·스트레인·ramp) / `레이스 예측`(목표 레이스 1카드에 4거리 묶음 + VDOT·Shape) / `능력·효율`(REC·CP·eFTP·VO2max 계열) / `수면` / `생체 신호`(SpO2·호흡·피부온도) / `심박 기준값`(RHR·HRV 야간/주간/상태·HRmax·LTHR 소스별) / `환경`. "레이스 준비도" 카테고리명은 쓰지 않는다(RRI와 이름 충돌).

### 2.3 메트릭 상세 `/library/metrics/:slug`
데스크톱 (8/4 2열):
```
‹ Library › 메트릭 › 훈련 준비도                                   [‹ Today로]
훈련 준비도  60 ● 보통                     UTRS · RunPulse utrs_v2 · 계산 06:10
[4주][3개월][6개월][1년]
┌──────────────────────── 8/12 ─────────────────┐┌──────── 4/12 ─────────┐
│ 80 ┤░░░░░░░░░░░░ 좋음 ░░░░░░░░░░░░░░░░░░░░░░░ ││ 이 지표는             │
│ 60 ┤----- 평균 71 -----------╱╲------●60      ││ 오늘 몸이 강한 훈련을 │
│ 40 ┤▓▓▓▓▓▓▓▓ 낮음 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ││ 받을 준비가 됐는지.   │
│     7월        8월        9월  │선택 9/27     ││ 좋은 범위 70–85       │
└────────────────────────────────────────────────┘│ 지금 60 — 90일 평균   │
[현재 60 · 9/27] [최고 89 · 8월 8일] [3개월 변화 −12% · −8점 ↓] │ 71보다 낮음           │
                                                  │ 행동: 강도 세션은 폼이 │
┌ 9월 27일 분해 ──────────────────────────────────┐│ −10 위로 회복된 뒤    │
│ 60점 — 폼(TSB)이 가장 크게 깎았어요 (−16점).    ││ [ⓘ 공식·정규화 규칙]  │
│ 다음은 짧은 수면 (−10점).                        │└───────────────────────┘
│ UTRS = 0.30·BB + 0.25·N(TSB) + … · utrs_v2 06:10 │
│ 요소      원시값        점수 가중 기여  손실      │
│ 폼(TSB)›  −9.0 (아침)   35 ██░ 25% 8.8  −16.3 ◀  │
│ 수면   ›  52점 · 4h14m  52 ██▌ 20% 10.4 −9.6     │
│ BB        기상 76       76 ███ 30% 22.8 −7.2     │
│ HRV    ›  107ms/평소79  90 ███ 15% 13.5 −1.5     │
│ 스트레스  전일 24       76 ██▊ 10% 7.6  −2.4     │
│ 이 날의 원천: 9/26 롱런 28.1km ›  9/27 수면 4h14m ›│
│ 무엇을 바꾸면(추정): 오늘 휴식+7시간 수면 → 내일 약 68 │
│ [RunPulse 계산] Garmin 값과 비교 →  Coach에게 묻기 →  │
└──────────────────────────────────────────────────┘
```
(수치는 설계 예시다. utrs_v2 재계산 후 실제 값으로 바뀐다. 기여 합계는 표시 반올림 오차를 허용한다. 와이어프레임의 `🔍 ☆ ★ ⓘ ▸ ▾ ‹`는 §C8 `Icon.svelte` 아이콘의 자리 표시다.)

**인라인 분해 패널 = §C3.2 4블록의 배치 변형(§C3 확장)**: 본문은 D2와 같은 `BreakdownView`다. ① 의미는 오른쪽 "이 지표는" 열(모바일은 접힘)이 맡고, 패널은 결론 1줄(§C3 확장 `conclusion`) → ② 공식 1줄(mono 12px, 버전·계산 시각) + 기여 행(감점 큰 순, 1위 `가장 크게 끌어내림`) → ③ 원천 Top 3 → 무엇을 바꾸면(추정, §C3 확장) → ④ 푸터 순서다. ④의 `추세·과거 보기 →`는 이미 이 화면이므로 생략하고, provider 비교 줄(`Garmin 값과 비교 →`, 비교 대상이 없으면 `RunPulse 단독 산출`), `Coach에게 묻기 →`, 출처 배지(§C6)를 둔다.

모바일: 헤더 → 기간 칩 → 차트(180px) → 요약 3칸(가로 스크롤 없이 3등분) → **분해 패널(선택일)** → "이 지표는"(접힘, 첫 방문만 펼침) → 비교 링크. 분해를 차트 바로 아래에 두어 스크럽과 분해를 한 화면에서 본다.

**예측 계열 상세**(F-DATA-06): 분해 패널이 "evidence" 형태로 바뀐다.
```
9월 27일 마라톤 예측  3:40  (3:26–4:03)  신뢰 낮음 36%
모델   Daniels 3:30 ━━━━━┓
       Tanda   3:51 ━━━━━┻━ 혼합 3:40 (약 51:49)
신호   대회 3:28 ×0.6 · 10K 2026-05-09 VDOT 46.2 ›
       훈련 3:36 ×0.2 · 활동 13420 ›     심박 3:32 ×0.2
끌어내리는 요인  [30km+ 롱런 12주 0회] [기준 대회 20주 전] [거리 외삽 ×4.2]
기온별  15℃ 3:40 · 20℃ 3:49 · 25℃ 3:57
```

### 2.4 웰니스 `/library/wellness/:date`
```
‹ 9월 26일 (금) │ 9월 27일 (토) · 오늘 │ ›          [달력]
월 화 수 목 금 토 일   ● ● ○ ● ● ◐ ●   (7일 회복 등급 점, 탭=이동)
회복 보통 — 수면이 짧았어요 (4h14m, 평소 7h02m보다 −2h48m). HRV는 평소보다 높음.
[수면 4h14m ›] [HRV 107 · 평소 79 ›] [BB 기상 76 ›]           ← §C2 DrillChip
┌준비도 60 ● 보통 ›┐  ┌수면 52점 · 4h14m  ▼−2h48m ─────────────┐
│부상위험 37 ● 주의›│  │ 깊은 57m│얕은 3h02m        │REM16│깸16 │
└──────────────────┘  └───────────────────────────────────────┘
[HRV 107ms ▲+35% 평소79 (밴드 76–111)] [안정심박 45 · 평소 39–49] [BB 기상76/최저16/충전+48]
[스트레스 29 · 21:42 기준] [걸음 22,971 · 21:42 기준]
30일 추세 (x축 공유, 스크럽 연동)
수면 점수 ─ p25–p75 띠 ─●   HRV ─ 띠 ─●   준비도 ─ 띠 ─●
```
데스크톱: 좌 1/3에 준비도·위험 카드, 우 2/3에 코어 카드 3열. 모바일: 1열 스택(헤드라인 → 근거 칩 → 준비도 2칸 → 수면 → 코어 2열 → 추세).
`/library/wellness`(날짜 없음)는 오늘 날짜로 `replaceState` 한다. 10-today의 D2 원천 링크 형식 `/v2/library/wellness?date=YYYY-MM-DD`도 받아서 `/library/wellness/:date`로 `replaceState` 한다(호환).

### 2.5 Provider 비교 `/library/providers` · `/library/providers/:group`
```
소스 비교   [4주][8주][12주]      같은 러닝을 소스마다 다르게 계산해요. ★ 값을 판단에 씁니다.
지표          Garmin     Intervals   RunPulse    차이(중앙)  n
훈련 부하 ›    110 AU     61 AU       55.7 AU    +80% ▲     14
LTHR      ›    168 bpm    —           177.5 bpm  +9.5bpm    —   (프로필값)
CTL       ›    —          (5/8 이후 없음) 72.7   척도 ×1.57  — 
VO2max·VDOT    53         —           44.5       정의 다름 · 비교 안 함 ⓘ
```
그룹 상세:
```
‹ 소스 비교 › 훈련 부하 (4주, 러닝 14쌍)
정의: Garmin=EPOC 기반 / Intervals=HR 부하 / RunPulse=HRSS(LTHR 기준)
[겹친 시계열: 활동별 점 3색 + 쌍 연결선]
날짜   활동             Garmin  Intervals  RunPulse
9/27   이지 9.3km ›     110.2   61         55.7
...
★ 규칙: 기간 내 러닝 그룹의 primary_source 최빈값(Garmin 11/14)
```

---

## 3. 클릭별 동작 명세

| 요소 | 제스처 | 결과 | 뒤로가기 | URL 상태 |
|---|---|---|---|---|
| 서브탭 | 탭 | 형제 화면 이동 | 이전 서브탭 | push |
| 브레드크럼 단계 | 탭 | 해당 단계 | 브라우저 기본 | push |
| `‹ Today로` 칩 | 탭 | `/today` | — | push |
| 검색 필드 | 입력 / `/` 키 | 카드 필터(150ms 디바운스) | 변경 없음 | `?q=` replace |
| 카테고리·Provider 칩 | 탭 | 그리드 필터 | 변경 없음 | `?category=&provider=` replace |
| 메트릭 카드 | 탭 | 상세 | 브라우저(필터 유지) | push |
| 카드 ☆ | 탭 / 길게(모바일) | 내 지표 고정 토글, 토스트 "고정됨 [되돌리기]"(§C5, 5s) | — | localStorage(try/catch) |
| 섹션 "모두 보기 ›" | 탭 | 카테고리 필터 | 이전 필터 | `?category=` replace |
| 기간 칩(상세·소스 비교) | 탭 | 차트 재조회, 선택일 유지 | 변경 없음 | `?period=`·`?days=` **replace** |
| 차트 | 호버(데스크톱) | §C1 미리보기(판독줄·툴팁) | — | — |
| 차트 | 탭/클릭, ←/→·Shift+←/→ 키 | §C1 고정 + 분해 패널을 그 날짜로 갱신(§C1 확장: 고정 = 분해 선택일). 해제(`×`·차트 밖 탭·같은 점 재탭·Esc) 시 패널은 마지막 날짜 유지 | 변경 없음 | `?date=` replace(§C3.3 보기 상태 규칙) |
| 차트 이벤트 마커(▲레이스·◆계산 변경) | 탭 | 판독에 이벤트 설명 | — | — |
| 분해 기여 행(드릴 가능) | 탭 | 입력 메트릭 상세, 같은 date·period 승계(§C3 확장: 인라인 패널에서는 스택 push 대신 D3 이동. Library 상세 자체가 추세 화면이므로) | 이전 메트릭 | push `/library/metrics/tsb?date=&period=` |
| 분해 "원천" 행 | 탭 | 활동 상세 / 웰니스 일자(§C3.2 ③ = D3) | 분해 패널 상태 복원 | push |
| "ⓘ 공식" / 약어 `MetricTerm` | 탭 | 팝오버(풀네임·정의·"자세히 →"). 내용은 분해 v2 `meaning`(§C3.2 ①과 같은 소스) | Esc 닫기 | — |
| "Garmin 값과 비교 →" | 탭 | `/library/providers/:group?days=28` | 상세 | push |
| 웰니스 ‹ › / 7일 점 | 탭, 스와이프(모바일) | 날짜 이동 | 이전 날짜 | `/library/wellness/:date` **replace** |
| 웰니스 코어 카드 | 탭 | 해당 메트릭 상세 `?date=` | 웰니스 같은 날짜 | push |
| 준비도·위험 카드 | 탭 | `/library/metrics/utrs?date=` (분해 열린 상태) | 웰니스 | push |
| 웰니스 추세 점 | 탭 | 그 날짜로 이동 | — | replace |
| 소스 비교 행 | 탭 | 그룹 상세 | 매트릭스(기간 유지) | push |
| ★ / 차이 칩 | 탭 | 인라인 1줄 설명(선택 규칙·차이 정의) | — | — |
| 쌍 목록 행 | 탭 | 활동 상세 `/library/:id/providers` | 그룹 상세 | push |

직접 진입 시 ←(브레드크럼 상위)는 저장된 마지막 필터 URL(sessionStorage)로 간다.

---

## 4. 지표 표기·설명 규격

### 4.1 값 포맷 (F-UX-01·F-UI-01·F-DATA-13)
규칙은 §C4다(시간·예측 기록·페이스·점수·부하·비율·백분율·백분위·변화량·U+2212·`.num`). 이 탭은 registry `format` 값으로 §C4 규칙을 고르는 진입점 `formatMetric(meta, value)` 하나만 둔다. 내부에서 §C4 함수(10 §7.1 `formatPrediction`·`formatSigned`·`formatByUnit` 등)를 호출하고 자체 규칙을 만들지 않는다.

| format_type | §C4 행 | 예 |
|---|---|---|
| `race_time` | 예측 기록 | `3:40 (3:26–4:03)`(신뢰 <0.5), `3:40:23`(≥0.5) |
| `pace` | 페이스 | `4:38/km` |
| `score` | 점수(0–100) | `60` |
| `ratio` | 비율 | `1.06` |
| `percent` / `percentile` | 백분율 / 백분위 | `105%` / `p78`(REC, F-DATA-10) |
| `load` | 부하(CTL/ATL) | `72.7`(AU는 정의 블록에만) |
| `per_week` | 변화량 | `+5.2/주`(ramp_rate, §7.3 C1) |
| `integer` | 정수 물리량·심박 | `22층`, `206 W`, `45 bpm` |

**§C4 확장**(§C4에 행이 없는 것)
- `race_time` 1시간 미만(5K·10K 예측): 신뢰 <0.5이면 `m:ss`를 5초 단위로 반올림하고 범위를 붙인다(`21:45 (20:50–22:40)`). ≥0.5이면 `m:ss`.
- `duration`(수면·누적 시간): `4h 14m`, `57m`. §C4 시간(`h:mm:ss`)은 기록·소요용이라 수면 길이에는 맞지 않는다 → §11 남은 충돌 2.
- 단위 표기: 값 크기의 0.6배, 최소 12px(§C8), fg-secondary.

### 4.2 표시 이름
API `name_ko`(한국어 의미어) + `abbr`(약어, 없으면 null). 표기는 §C3.1과 같이 한국어 이름 + 약어(작게): `훈련 준비도 UTRS`. 용어는 10 §4를 따른다(`체력(CTL)`, `피로(ATL)`, `폼(TSB)`). 상세 제목은 `훈련 준비도`, 부제는 `UTRS · Unified Training Readiness Score · utrs_v2`. 분해 라벨도 같은 이름을 쓴다(`(parent: utrs)` 등 내부 ID 노출 금지). 프론트 `LABELS` 하드코딩은 삭제한다(F-UX-12, F-UI-11).

**출처(SSOT, 2026-10-03 개정)**: `src/utils/metric_labels.py`의 `METRIC_LABELS: dict[str, MetricLabel]`(키 = registry 정규 이름, `MetricLabel(name_ko, abbr=None)`). `metric_registry.py`(수집·정규화 SSOT)와 `bands.py`(등급 SSOT)처럼 표시 문구만 따로 둔다. 서비스 `metric_display.display_meta()`가 이 표를 읽어 `name_ko`·`abbr`를 내려주고, 임시 `_NAMES` 8개 표는 삭제한다. `scripts/gen_metric_dictionary.py`는 이 표를 읽어 사전에 "표시 이름" 열을 만든다(사전은 파생 문서). 계산기 `display_name`(예: `PMC (ATL/CTL/TSB)`)은 계산기(알고리즘) 이름으로 남고 화면 표시에는 쓰지 않는다.
- 범위·순서: 일별(daily) 84개 전부를 먼저 명시 등록한다(카드·Today 노출 대상). activity·weekly 지표는 폴백을 허용하고 20 활동 상세 작업 때 채운다.
- 폴백: 표에 없으면 `name_ko` = registry `description`에서 `(parent: …)`를 지운 값, 그것도 비면 정규 이름. `abbr` = null.
- 확장: `description_short`·`action_hint`(문구)는 같은 `MetricLabel`에 선택 필드로 얹는다. `format`·`decimal_places`는 `metric_display.py`의 단위 규칙 + 이름별 예외, `bands`는 `bands.py`에 둔다(문구·숫자 규칙·등급을 분리). 항목이 늘어 300줄을 넘으면 `metric_labels/` 패키지(scope별 파일)로 나누고 공개 API는 유지한다.
- 일관성 테스트(`tests/test_metric_labels.py`): 키 ⊆ registry, daily 84개 전부 등록, `name_ko` 비어 있지 않음·`(parent:` 없음·약어 괄호 미포함, 같은 카테고리 안 `name_ko` 중복 없음, `abbr`는 공백 없는 ASCII ≤8자(`VO2max`·`eFTP` 허용), 10 §4 용어 고정(`ctl`→`체력`/`CTL`, `atl`→`피로`/`ATL`, `tsb`→`폼`/`TSB`).
- 검토했으나 채택하지 않음: (c) 계산기 `display_name` — 일별 84개 중 계산기 산출은 37개뿐(수면·HRV·안정시 심박·Body Battery 등 외부 원천은 계산기 없음)이고, 계산기 1개가 여러 지표를 내거나(PMC→ctl·atl·tsb·ramp_rate) 여러 계산기가 같은 지표를 낸다(`race_pred_*` 4개). (a) `MetricDef`에 필드 추가 — 레지스트리가 이미 522줄(300줄 규칙 초과)이고, 문구 수정이 수집 정규화 SSOT를 건드리게 된다. DB 테이블 — 코드와 함께 버전 관리되는 정적 문구라 마이그레이션 비용만 생긴다.

### 4.3 설명 4요소 (U5, F-UX-04)
상세 "이 지표는" 블록과 `MetricTerm` 팝오버가 같은 데이터를 쓴다.
1. **무엇**: 레지스트리 `description_short`(40자 이내 평이문). 예: CTL "최근 6주 훈련량이 쌓인 정도(τ=42일 지수가중 평균)".
2. **좋은 범위**: 서버 `bands`(차트 띠와 같은 소스).
3. **내 값 해석**: `지금 {값} — {등급}. 90일 평균 {mean}보다 {높음/낮음}` (개인 기준선 p25–p75 대비).
4. **행동**: 레지스트리 `action_hint`(등급별 1문장). 없으면 블록에서 생략한다(빈 문구 금지).
브라우저 카드 2행에는 1 또는 3을 한 줄로 쓴다.

### 4.4 등급·색
- 등급·의미색은 §C7이다. 서버 `status ∈ {danger, caution, neutral, good, great}` + `status_label`로만 렌더하고, 라벨 문구는 레지스트리가 메트릭별로 정한다(예: TSB `생산적 부하`). 색만으로 구분하지 않고 라벨·모양(●▲)을 병기한다.
- 등급 산출은 **서버 레지스트리 `bands`만** 사용한다. `metricMeaning.ts`의 밴드·`status.ts` 사용처는 제거한다(F-UX-05, F-DATA-02, 10-today F-DATA-04).
- TSB 밴드는 10-today §4의 registry 단일 정의를 따른다: `< −30` danger `과부하` · `−30~−10` good `생산적 부하` · `−10~+5` neutral `유지` · `+5~+25` great `신선`(D−21 이내 `레이스 최적`) · `> +25` caution `휴식 과다`. 테이퍼·레이스 주간 국면의 재판정도 서버가 한다. TSB 표시는 **아침 기준**(`tsb_morning`)이다.
- RTTI는 레지스트리 ranges(overload 100–130, danger 130+)를 쓰고 등급을 표시한다(F-DATA-08).
- 변화량 색: §C4대로 화살표는 방향만 뜻하고, 좋고 나쁨은 `higher_is_better`로 정한 차이 색 + 라벨로 표시한다. `null`이면 무채색이다. 차이 색은 §C7 확장 `--delta-better/worse`(20 §11 제안, 99-summary D1b)를 쓰고 의미색(green/amber)을 빌려 쓰지 않는다 → §11 남은 충돌 1.

### 4.5 출처 배지 (F-UI-03, P3)
표기·색·위치 규칙은 §C6이다(글자 배지 = 테두리 + 글자, 블록 출처가 같으면 헤더에 한 번, 기준일이 다르면 `Garmin · 9/26`, 30일 넘으면 회색 + `오래된 값`).
- 이 탭 적용: 기본 출처(RunPulse 합성)는 섹션 헤더에 `RunPulse 계산` 한 번(§C6 확장: 뒤에 `· 기본`을 붙여 기본 provider임을 밝힌다). 다른 출처인 카드만 라벨 줄 오른쪽에 `Garmin` 배지를 붙인다(좁은 모바일 카드는 글자 약어 `G`).
- RunPulse 값의 `algorithm_version · 계산 시각`은 §C3.2 ② 공식 줄·§C6 D2 푸터와 같은 문자열을 상세 부제에도 쓴다(§C6 확장).
- 폴백 계산(예: avg_hr 폴백 relative_effort)은 `추정` 배지를 단다(§C6 확장, §7.3 C3).
- Provider 비교 매트릭스 셀에서 30일 넘게 값이 없으면 §C6 `오래된 값` 대신 `5/8 이후 없음`으로 마지막 일자를 적는다(§C6 확장, F-DATA-12).

---

## 5. 차트 규격

공통 동작·축·툴팁·방향·참조선·결측·빈 데이터·최소 크기는 §C1 ChartScrub이다. `TrendChart`·`Sparkline`은 `lib/chart/scrub.ts` 코어 위에 올린다. 시리즈색은 §C7 `--series-1/2/3`, 등급 밴드 색은 §C7 의미색이다. 아래는 이 탭의 설정과 §C1 확장만 적는다.

| 항목 | 이 탭 설정 |
|---|---|
| y축 | §C1 눈금 규칙. **§C1 확장**: 라벨은 플롯 밖 좌측 거터(모바일 32px, 데스크톱 44px), 격자선 opacity .08 |
| x축 | 3개월·6개월 `7월`(§C1 ≤6개월), 1년 `25.10`(§C1 >6개월). **§C1 확장**: 4주 기간은 주 경계 `9/1 9/8`(월 경계만으로는 눈금이 1~2개라 부족) |
| 방향 | §C1 `invert`(예측 기록·페이스·RHR, 축 캡션 `빠름 ↑`). **§C1 확장**: CIRS처럼 "높을수록 나쁨"인 위험 점수는 반전하지 않고 밴드 색으로 표현한다 |
| 포맷 | 눈금·판독줄·툴팁 모두 `formatMetric`(§4.1 → §C4) |
| 마커 | 마지막 점 r=3 + 값 라벨. **§C1 확장**: 이벤트 마커 ▲(레이스)·◆(계산 버전 변경, 예: `PMC v2 적용`). 판독줄에 이벤트 설명 |
| 밴드·기준선 | §C1 참조선: 등급 밴드 = 서버 `bands`(§C7 의미색 opacity .08, 라벨은 오른쪽 거터 24px, 11px), 평균 = 수평 점선 + 라벨(`평균 71`, `--series-2`). 웰니스 개인 기준 p25–p75 띠 |
| 3개월 이상 | **§C1 확장**: 7일 이동평균(굵게, `--series-1`) + 일별(opacity .35) |
| 크기 | 상세: 모바일 180px, 데스크톱 `clamp(220px, 28vw, 320px)`. 웰니스 small multiples 각 120px(§C1 최소), x축 공유·스크럽 연동(§C1 확장: 한 ChartScrub이 3개 패널을 구동) |
| 접근성 | §C1 키보드·`aria-live`. 동적 `aria-label` "UTRS 3개월: 현재 60, 최고 89(8월 8일), 최저 37" |
| 색 | `.svelte` 안의 hex 하드코딩 금지(lint), 미정의 변수 금지(§C8 Stylelint) |
| 빈 데이터 | §C1: 점 <2개면 `데이터 수집 중 (n/필요 일수)` + 행동 링크(예: `데이터 수집 중 (12/28일) · 활동 가져오기 ›`). 결측 2일 초과는 선을 끊는다 |

**스파크라인(카드)**(F-UI-02, F-UX-14): 높이 48px(§C1). **§C1 확장**: y 범위 = `max(데이터 범위, min_span)`, 가운데 정렬. `min_span`은 레지스트리 값(bpm 5, 페이스 10초, 예측 2%, 점수 10, 비율 0.2). 방향 반전은 §C1과 같다. 끝점 원 r=2.5(§C7 의미색 = 서버 status), 선은 `--series-2`. 캡션 `14일 · ▼6분`. 모든 값이 같으면 `고정값(프로필)` 또는 `계산 안 됨`(값 null 비율 >50%)으로 구분한다. 카드 안 스파크라인의 스크럽 여부는 §11 남은 충돌 3.

---

## 6. 로딩·빈·오류 상태

| 블록 | 로딩 | 빈 | 오류 |
|---|---|---|---|
| 브라우저 그리드 | §C5 진행바 + `Skeleton.svelte`로 칩 줄 + 카드 8장(최종 치수 예약). 내 지표 먼저 스트리밍 | 검색 결과 0: "‘{q}’와 맞는 지표가 없어요" + [검색 지우기] | §C5 블록 오류 `불러오지 못했어요 · [다시 시도]` + 접힌 상세. 캐시가 있으면 SWR로 캐시 표시 + 헤더 필 `업데이트 중`/`9:10 기준` |
| 상세 차트 | 차트 높이 예약 스켈레톤(§C5 차트 영역 프리미티브) | §5 빈 데이터(§C1) | 차트 자리 §C5 오류 + [다시 시도] |
| 분해 패널 | 차트 pointerdown 시 prefetch. 패널 높이 예약(행 5개) → 레이아웃 점프 0 | §C3.2 빈 상태: ②·③이 모두 비면 `이 지표는 {원천}에서 직접 받은 값이에요` + 원천 링크 | 패널 내 §C5 오류 + [다시 시도], 차트는 유지 |
| 웰니스 | 카드·칩 스켈레톤 | 해당 날짜 기록 없음: "9월 20일 웰니스 기록이 없어요" + [가장 가까운 날짜로] | §C5 블록 오류 |
| 소스 비교 | `ProviderComparison`의 기존 스켈레톤을 페이지가 `loading`으로 연결 | 쌍 n=0: "이 기간에 두 소스가 모두 기록한 러닝이 없어요" + [기간 늘리기] | §C5 블록 오류 |

로딩·빈·오류·쓰기 피드백의 공통 문법은 §C5다(라우트는 핵심 API 1개만 await, "데이터 없음"과 "불러오기 실패" 구분, 쓰기 성공 토스트 + [되돌리기] 5s).

---

## 7. 변경 컴포넌트·API·계산 규칙

### 7.1 프론트엔드 (frontend/src)
| 파일 | 변경 |
|---|---|
| `routes/library/+layout.svelte` | **신규**. 서브탭/브레드크럼 공통, `from` 칩 |
| `routes/library/metrics/+page.svelte`·`+page.ts` | 검색·URL 필터(replace)·내 지표·카테고리 재편·2/4열 그리드·배지 규칙·섹션 제목 14px semibold·접기 행 44px |
| `routes/library/metrics/[slug]/+page.svelte`·`+page.ts` | 8/4 레이아웃, `?date=`, 요약 카드 문법 통일, 인라인 `BreakdownPanel`, "이 지표는", 기간 replace·승계 |
| `routes/library/wellness/[date]/+page.svelte`·`+page.ts` | **신규**. 기존 `wellness/+page.*`는 오늘로 리다이렉트 |
| `routes/library/providers/+page.svelte` | 단위·오른쪽 정렬·차이 칩·행 링크, `max-w-[760px]` |
| `routes/library/providers/[group]/+page.*` | **신규** 쌍 목록·겹친 시계열 |
| `lib/format.ts` | `formatMetric(meta, v)` 추가(registry `format` → §C4 함수 디스패치, 10 §7.1 함수 재사용). `formatUnitValue`는 내부 사용 |
| `lib/metricMeaning.ts` | 밴드·LABELS 삭제(10 §7.1과 같음). `displayLabel` 대신 API `name_ko`·`abbr`(백엔드 출처 `src/utils/metric_labels.py`, §4.2. 백엔드 영향: `src/services/metric_display.py` `_NAMES` 삭제, `scripts/gen_metric_dictionary.py` 표시 이름 열) |
| `lib/components/TrendChart.svelte`·`lib/trendChart.ts` | §C1 `ChartScrub` 코어(10 S4) 위로 이관. 이 탭 추가분: bands·refLines·events·이동평균·selectedDate/onSelect(`?date=` 연동) |
| `lib/components/Sparkline.svelte` | §C1 코어 사용 + `minSpan`, 끝점 |
| `lib/components/MetricBreakdown.svelte` | 10 §C3의 `DrillHost`·`DrillPanel`·`BreakdownView`로 대체. 이 탭은 `BreakdownView`를 감싼 인라인 컨테이너 `BreakdownPanel.svelte`(신규, §C3 확장)만 추가한다 |
| `lib/components/ContributionBars.svelte` | **신규** §C3.2 ② 기여 막대(`BreakdownView`가 사용, Today D2와 공유) |
| `lib/components/PredictionEvidence.svelte` | **신규** 예측 evidence(§C3 확장: 예측 계열 ② 블록 변형, Today 예측 D2와 공유) |
| `lib/components/MetricTerm.svelte` | **신규**(Library 고유. Today는 별도 ⓘ 없이 D2 ①을 쓴다) 약어 ⓘ 팝오버, 내용은 분해 v2 `meaning` |
| `lib/components/ProviderComparison.svelte` | 단위 캡션·★ 슬롯·차이 칩·`ondrill` 연결·§C8 아이콘·§C6 배지 |
| `layout.css` | 변경 없음. §C7 series·의미색 토큰과 §C8 fg-muted 대비·폰트는 10 S1에서 정의한다. 이 탭은 §C7 확장 `--delta-better/worse`만 요청(§11) |

### 7.2 API (/api/v1, 읽기 전용 GET)
**(a) `GET /library/metrics`** — 각 metric에 메타를 추가한다.
```json
{"name":"race_pred_marathon_sec","name_ko":"마라톤 예측","abbr":null,
 "format":"race_time","unit":"sec","higher_is_better":false,"decimal_places":0,
 "value":13223,"range":{"low":12360,"high":14566},"confidence":0.36,
 "status":null,"status_label":null,"confidence_label":"신뢰 낮음",
 "description_short":"최근 기록·훈련·심박으로 추정한 완주 기록",
 "sparkline":[...],"spark_min_span":0.02,"change":{"abs":-360,"pct":-2.7,"days":14},
 "provider":"runpulse:formula_v1","is_default_provider":true,"last_value_date":"2026-09-27"}
```
필드 이름은 10 §7.3 계약과 같다: `name_ko`, 평평한 `status`·`status_label`(§C7 5단 키, 등급이 없는 메트릭은 null). 예측의 신뢰 수준은 등급이 아니므로 `status`에 넣지 않고 `confidence`·`confidence_label`로 따로 준다. `name_ko`·`abbr`의 출처와 폴백은 §4.2(`metric_labels.py`)이고, 목록·추세 `meta`·분해 v2가 같은 값을 쓴다.

**(b) `GET /library/metrics/:slug/trend?period=`** — `meta`(위와 동일), `bands:[{max,status,label}]`(10 §7.3 `meaning.bands`와 같은 모양, 오름차순), `baseline:{mean,p25,p75,days:90}`, `events:[{date,type:"race"|"algo_change",label}]`를 추가한다. `peak`는 `best`(방향 반영)와 `worst`로 바꾼다. `change`는 선택 기간 기준으로 계산한다.

**(c) 분해 v2** — 계약은 10 §7.3 `GET /library/metrics/{slug}?scope_type=daily&scope_id=YYYY-MM-DD&explain=1`(§C3 렌더 계약) 하나다. `metrics_service.get_metric_breakdown`을 확장한다. 아래는 이 탭이 쓰는 필드와 §C3 확장 필드(`conclusion`, `evidence`)의 예시다.
```json
{"slug":"utrs","name_ko":"훈련 준비도","abbr":"UTRS","value":60,"status":"neutral","status_label":"보통",
 "meaning":{...},
 "formula":{"text":"0.30·BB + 0.25·N(TSB) + 0.20·수면 + 0.15·N(HRV) + 0.10·(100−스트레스)",
            "version":"utrs_v2","computed_at":"2026-09-27T06:10:00+09:00",
            "terms":[{"slug":"tsb","label":"폼(TSB)","raw":{"value":-9.0,"unit":"","note":"아침 기준"},
              "normalized":35,"weight":0.25,"contribution":8.8,"loss":-16.3,"drill":"m.tsb"}]},
 "conclusion":{"top_loss":"tsb","text":"폼(TSB)이 가장 크게 깎았어요 (−16점)"},
 "sources":[{"type":"activity","id":17414,"date":"2026-09-26","label":"롱런 28.1km","effect":"폼 −6"},
            {"type":"wellness_day","date":"2026-09-27","label":"수면 4h14m"}],
 "provider":{...},"compare":[...],"links":{"trend":"..."},"evidence":null}
```
- 기존 `children`·`inputs` 배열은 `formula.terms`로 대체하고 한 릴리스 뒤 제거한다. `terms[].drill`은 §C3.3 토큰(`m.tsb`)이고, 인라인 패널은 이를 `/library/metrics/tsb?date=`로 바꿔 이동한다(§3).
- 입력 조회 버그를 고친다. 현재는 `c.name == slug`로 계산기를 찾아 `darp`가 산출한 `race_pred_marathon_sec`의 입력이 비어 있다. **`slug in c.produces`**로 찾는다.
- 계산기별 **explainer**(서비스 계층, `src/services/metric_explainers.py` 신규)가 `json_value`를 구조화한다. 예측 계열 evidence:
```json
"evidence":{"range":{"low":12360,"high":14566},"confidence":0.36,
 "models":[{"name":"daniels","value":12612},{"name":"tanda","value":13864}],"blend":"≈51:49 (역산)",
 "signals":[{"key":"race","value":12479,"weight":0.6,"activity_id":1010,"date":"2026-05-09"},
            {"key":"work","value":12935,"weight":0.2,"activity_id":13420},{"key":"hr","value":12700,"weight":0.2}],
 "limiting":["30km+ 롱런 12주 0회","기준 대회 20주 전","거리 외삽 ×4.2","모델 간 차이 9.5%"],
 "by_temp":[{"c":15,"value":13223},{"c":20,"value":13716},{"c":25,"value":14248}]}
```
  explainer는 json 키가 없으면 해당 필드를 생략한다(예측 모델 r3 개편과 독립. `project_phase7_handoff`의 예측 리뉴얼이 json 스키마를 바꾸면 explainer만 고친다).
- `sources`: TSB·CTL·ATL은 선택일 기준 최근 7일 중 부하 상위 활동 3개(TRIMP와 폼 기여 추정 `−α_ATL·load`, α = `1/τ`, D1). UTRS·CIRS는 해당 일자 웰니스 + 상위 부하 활동이다.

**(d) `GET /library/wellness?date=`** — `baselines:{hrv_last_night:{mean7,p25,p75,garmin_band:[76,111]},resting_hr:{...},sleep_duration_sec:{mean30}}`, `as_of:{avg_stress:"21:42",steps:"21:42"}`, `sleep_stages:{deep,light,rem,awake}`, `body_battery:{wake,low,charged}`, `readiness:{utrs:{value,status},cirs:{value,status}}`, `nav:{prev,next}`(기록 있는 날짜), `week:[{date,status}]`를 추가한다.

**(e) `GET /library/providers/matrix?days=`** — 응답을 쌍 기반으로 재정의한다(§7.3 C4).
```json
{"days":28,"sport":"running","rows":[{"slug":"training_load","label":"훈련 부하","unit":"AU",
  "comparable":true,"cells":{"garmin":{"metric":"training_load","median":98.0,"latest":110.2},
  "intervals":{"metric":"training_load","median":58.0},"runpulse:formula_v1":{"metric":"hrss","median":52.1}},
  "pairs_n":14,"diff":{"ref":"runpulse:formula_v1","median_pct":80.2,"iqr_pct":[61,95]},
  "preferred":{"provider":"garmin","reason":"기간 내 러닝 그룹 primary_source 최빈(11/14)"}}]}
```
**(f) `GET /library/providers/pairs?group=&days=`** **신규** — `[{date, group_id, activity_id_by_provider:{...}, values:{...}}]`.

### 7.3 계산 규칙 수정안 (코드 수정은 구현 단계에서. 여기서는 규칙만 정한다)

모든 RunPulse 계산기는 CalcContext API만 사용한다(ADR-009). 버전 문자열을 올려 재계산 전후를 구분한다.

**C1. PMC — CTL/ATL 시간상수와 연속 재귀** (F-DATA-01, 10-today F-DATA-01·03)
- 현행: `pmc.py:51-52` `α = 2/(N+1)` → α_CTL 0.0465(실효 τ≈21), α_ATL 0.25(τ≈4). 날짜마다 49일 창을 0부터 다시 계산한다.
- 규칙:
  - `α_CTL = 1/42`, `α_ATL = 1/7`(설계 원문 `v0.2/.ai/metrics.md`의 `CTL(n)=CTL(n−1)+(TRIMP−CTL(n−1))/42`). **DECISIONS `[P7-UX-REVIEW-0928]` D1 확정**(`1−e^(−1/τ)`는 채택하지 않음. V3 병행 비교에서 ATL 편차가 체계적으로 크면 재검토한다는 조건은 그 ADR에 있다). 레지스트리에 `time_constant_days`를 명시한다. 레이스 아침 투영·계획 CTL 궤적(31 R9)도 같은 α를 쓴다.
  - **연속 재귀**: `CTL_d = CTL_{d−1} + (load_d − CTL_{d−1})·α`. `CTL_{d−1}`은 전일 저장값(`ctx.get_latest_daily_metric`)을 쓴다. 전일 값이 없거나 `algorithm_version`이 다르면 최초 부하일부터 전체 재계산한다. 시드는 0(이 계정은 2023-10-29부터 3년치라 시드 영향이 없다).
  - 저장값 2종: `ctl/atl/tsb`(당일 종료 기준, 오늘 값은 경과 비율 감쇠 `tsb_live`로 차트 잠정 점에만 쓴다, 10 §7.2)와 **`tsb_morning` = CTL_{d−1} − ATL_{d−1}**(하루 고정). 권고·등급·UTRS 입력은 `tsb_morning`을 쓴다.
  - `ramp_rate = CTL_d − CTL_{d−7}`(주간). 오늘 잠정값은 차분에서 제외한다. 단위 `/주`.
  - version `pmc_v2`.
- 예상치(PMC만 교정, 현행 TRIMP 입력, DB 읽기 전용 재현):

| 날짜 | 저장(v1) CTL/ATL/TSB | v2 CTL/ATL/TSB | v2 tsb_morning |
|---|---|---|---|
| 9/20 (롱런 TRIMP 269) | 79.2 / 123.2 / −44.0 | 74.3 / 102.7 / −28.4 | −5.4 |
| 9/21 | 75.0 / 92.4 / −17.4 | 72.5 / 88.0 / −15.5 | −28.4 |
| 9/23 | 67.7 / 52.0 / +15.8 | 69.1 / 64.7 / +4.4 | −4.6 |
| 최근 90일 TSB 범위, −30 미만 일수 | −70.0~+24.8, 15일 | −46.0~+16.0, 7일 | — |
  참고: v1의 ATL은 `α=0.25` 전체 이력 재귀와 정확히 일치하고, CTL은 49일 절단 때문에 전체 이력 재귀(84.4)보다 5.2 낮았다(9/20).

**C1-b. TRIMP 계수**: 10-today F-DATA-02의 수정(`0.64·e^(1.92x)`, version `trimp_v2`)을 **같은 재계산에 포함**한다. TRIMP가 바뀌면 C1 예상치의 수준이 달라지므로, 검증은 2단계로 한다(§7.4 V2).

**C2. ACWR — PMC와 분리한 EWMA** (F-DATA-01, F-DATA-08)
- (정의 충돌 → §11 남은 충돌 4. 현행 `acwr.py`는 `ATL/CTL`, 31 R9 설명은 `7/42`, 10 §7.2는 "EWMA `2/(N+1)` 유지"라고만 적었다.) ACWR은 Williams(2017) EWMA-ACWR 관례를 따른다: acute λ=2/(7+1), chronic λ=2/(28+1), `ACWR = EWMA7/EWMA28`. PMC의 CTL/ATL을 재사용하지 않는다. 입력은 `ctx.get_daily_load`, 연속 재귀 방식은 C1과 같다. 기존 게이트(CTL<10, 28일 이력)는 `EWMA28 < 10`으로 옮긴다. version `acwr_ewma_v2`.
- CIRS(10-today F-DATA-12 규칙과 통일): ACWR 위험 구간식(<0.8 → 15, 0.8~1.3 → 0, 1.3~1.5 → 0→50 선형, >1.5 → 50→100, 2.0에서 100), 피로 항 = `clamp((ATL/CTL − 1)·200, 0, 100)`, 연속일은 러닝만. 라벨 "피로도(CTL−TSB)"는 "급성/만성 비율"로 정정. version `cirs_v2`.

**C3. activity-scope RunPulse 계산은 그룹당 1회** (F-DATA-04)
- 현행: 같은 `matched_group_id`의 사본(Garmin·Intervals·Strava)마다 따로 계산해 `is_primary=1`로 각각 저장한다. 실측(읽기 전용): 사본이 2개 이상인 396개 그룹 중 **relative_effort 395개, wlei 140개, trimp·hrss 27개, aerobic_decoupling 20개, runpulse_vdot 14개**가 사본 간 10% 넘게 다르다. 원인은 존 시간이 없는 사본의 avg_hr 폴백(`relative_effort.py:48-65`)과 사본별 duration(moving/elapsed) 차이다.
- 규칙:
  1. 엔진은 `v_canonical_activities`(그룹 대표) id에만 activity-scope 계산기를 실행한다. 사본 id에는 RunPulse 행을 만들지 않는다.
  2. 입력 병합: 대표 사본에 없는 입력(HR 존 시간·스트림)은 같은 그룹 다른 사본에서 채운다. CalcContext에 `get_group_metric(name)`·`get_group_streams()`를 추가한다(ADR-009 준수. 설계 확정은 system-architect).
  3. 폴백 결과는 `confidence ≤ 0.6`, `json_value.method = "avg_hr_fallback"`으로 저장하고 UI에 `추정` 배지를 단다.
  4. 그룹 대표가 바뀌면(재매칭) 해당 그룹을 재계산한다.
  5. `check_data_consistency.py`에 두 검사를 추가한다: "그룹당 RunPulse activity 행 1개", "SEMANTIC_GROUPS 멤버가 metric_store에 실재".

**C4. Provider 매트릭스 — 같은 활동 쌍 비교** (F-DATA-03, F-DATA-05)
- 현행 `provider_matrix_service.py:83-94`: provider마다 "가장 최근 활동에서 처음 찾은 값"을 채운다. 셀이 서로 다른 활동에서 온다(Garmin 7.18 = 9/27 **수영** 17445, RunPulse 55.7 = 같은 날 러닝의 Intervals 사본 17404). `cells`가 provider 키라 같은 provider의 hrss/wlei/rtti 중 먼저 찾은 것이 들어간다. 사본 순회가 id 순이라 RunPulse 값이 비대표 사본에서 온다.
- 규칙:
  1. 대상: 기간 내 `activity_type IN ('running','trail_running','treadmill')`인 canonical 그룹.
  2. 행 = 그룹 정의(메트릭 1개/provider, 같은 물리량·단위). 셀 = 기간 내 그 provider 값의 중앙값 + 최신값.
  3. 차이 = **양쪽 값이 모두 있는 그룹 쌍**의 `(a−b)/b` 중앙값·IQR·n. n<3이면 판정하지 않는다. ⚠는 |중앙값|>15%일 때만 표시한다.
  4. RunPulse 값은 C3 이후 그룹당 1개이므로 사본 선택 문제가 사라진다.
  5. 그룹 정의 교정(`src/utils/metric_groups.py`): `training_load` 멤버를 `training_load`(intervals, 실재 612건)·`training_load`(garmin)·`hrss`(runpulse)로 한다. rtti·wlei는 제외(일 단위 또는 다른 양). `running_efficiency`는 EF 단위를 통일하고(RunPulse EF ÷1000 등 환산 규칙 명시) REC(백분위)는 뺀다. `vo2max`와 `vdot`은 `comparable:false` 설명 행으로 두고 정의를 함께 보여 준다(32.6 = 이지런 활동 VDOT, 44.5 = 일 단위 예측 VDOT, 53 = Garmin 기기 VO2max). `seasonal_performance`(fearp)는 `pace` 포맷. 추가 행: LTHR(자체 177.5 vs Garmin 168), HRmax, CTL(RunPulse vs Intervals, daily scope, 척도 비율로 표기).
  6. 기간 선택은 표본 범위를 바꾸므로 4/8/12주 결과가 달라진다.

**C5. 마라톤 예측 분해** (F-DATA-06)
- 계산 변경은 없다. §7.2(c)의 `produces` 조회 수정과 explainer로 해결한다. 목록·Today의 예측 헤드라인 포맷(`race_time` + 범위 + 신뢰)은 §4.1을 따른다. 추세 차트에는 기준 대회 교체일을 `events`로 표시한다(`race_pred_vdot.json`의 기준 activity가 바뀐 날).

**C6. UTRS — HRV 개인 기준선, 아침 스냅샷** (F-DATA-07)
- 현행 `utrs.py:57-60`: `hrv_weekly_avg`를 절대 범위 20~100ms로 정규화한다(주간 80 → 75). 야간 급락(9/22 44ms, 기준선 하한 69)에도 HRV 성분은 거의 움직이지 않았다.
- 규칙:
  - `z = (ln HRV_night_d − mean(ln HRV_night, d−7..d−1)) / SD(ln HRV_night, d−60..d−1)` (`ctx.get_wellness_series(60)`).
  - 점수 매핑(구간 선형): z ≥ +1.0 → 90(상한), −0.5 ≤ z < +1.0 → 70~90, −1.5 ≤ z < −0.5 → 30~70, −3.0 ≤ z < −1.5 → 0~30, z < −3 → 0.
  - 이력 <14일이면 Garmin 균형 밴드(`hrv_baseline_balanced_low/upper`) 내 위치로 대체(밴드 안 70~90, 하한 미만은 하한 대비 비율)하고 confidence를 0.7배로 낮춘다.
  - 재현(읽기 전용): 9/22 야간 44ms, 7일 기준 87ms, SD .196 → z −3.46 → **0점**(현행 71). 9/27 야간 107ms, 기준 79ms → z +1.51 → **90점**(현행 75).
  - **아침 스냅샷**: TSB는 `tsb_morning`, 스트레스는 **전일** `avg_stress`, BB는 기상 값(`body_battery_high`를 "기상 시"로 라벨, 수집 필드가 생기면 교체). 수면 종료 후 첫 계산 값을 그날의 UTRS로 고정하고, 이후 재계산에서 입력이 같으면 값도 같다.
  - BB와 HRV·수면의 이중 계산 문제(10-today F-DATA-11)는 가중치 재설계가 필요하므로 이 탭에서는 **보류**한다. 가중치는 현행을 유지한다(99-summary D7 권장안: 1차는 HRV z-score·아침 스냅샷만, BB 제외는 백테스트 후 결정).
  - version `utrs_v2`. json에 원시 입력(`raw`)을 함께 저장해 분해 v2의 "원시값" 열이 추가 조회 없이 나오게 한다.

### 7.4 재계산·검증 절차

**R0 준비**
1. 컨테이너 안에서 사용자 DB를 백업한다: `running.db` → `running.db.bak-20260927-pmc_v2`(대상 계정 전부).
2. 기준 스냅샷(읽기 전용 SQL): 최근 400일 daily `ctl/atl/tsb/acwr/utrs/cirs/rtti/race_pred_*`, activity-scope RunPulse 행 수·그룹별 편차를 CSV로 남긴다. `python -m src.metrics.cli status` 출력도 저장한다.

**R1 단위 테스트(구현과 함께 추가)**
- PMC: 무부하일 비율 CTL 0.97619(=1−1/42)·ATL 0.85714(=1−1/7), 오차 1e−4. 증분 계산(전일 이어받기)과 전체 재계산의 차이 ≤0.05.
- `tsb_morning`이 같은 날 시각(06:00/21:00)과 무관하게 같다.
- ACWR: 7일 부하 100 연속 후 값 1.0. EWMA 계수 2/8·2/29.
- TRIMP 원문 수치(10-today): x=0.5 → 0.836/분, x=0.9 → 3.243/분.
- relative_effort: 존 시간 없는 사본만 있는 그룹은 `method=avg_hr_fallback`, conf ≤0.6.
- UTRS HRV: 위 9/22·9/27 재현값(0, 90). 이력 10일 → Garmin 밴드 대체.
- 매트릭스: 수영 활동이 비교에 들어가지 않는다. n<3이면 diff=null.
- 분해: `race_pred_marathon_sec` evidence 필드 존재. `utrs` contributions 합 = value ±0.5.

**R2 스테이징 재계산(DB 복사본)**
1. 복사본에 **PMC v2만** 적용해 재계산한다. → V2-a 확인.
2. TRIMP v2 + C2·C3·C6를 추가 적용해 전체 재계산한다: `docker exec runpulse-runpulse-1 python -m src.metrics.cli recompute-all`(계정별). 순서는 엔진 위상 정렬(activity-scope → daily)을 따른다. 사본의 기존 RunPulse activity 행은 `clear_runpulse_metrics` 후 재생성되므로 남지 않는다.
3. 예측 계열(`darp*`)은 `ctl`에 의존하는 변형(`darp_r4_asym`)이 있어 값이 바뀐다. 전후 비교표를 예측 리뉴얼(Phase 7 r3) 담당 문서에 전달한다.

**R3 검증 쿼리·기준**
| ID | 검증 | 합격 기준 |
|---|---|---|
| V1 | 무부하일 CTL_d/CTL_{d−1}, ATL 비 | 0.976±0.001, 0.857±0.001 (현행 0.953/0.750) |
| V2-a | PMC만 적용한 복사본의 9/20·9/21·9/23 값 | §7.3 C1 표와 ±0.2 |
| V2-b | TRIMP v2까지 적용 후 90일 TSB 범위·−30 미만 일수 | 기록만 한다(판정 없음). DECISIONS 전후 표에 남김 |
| V3 | Intervals CTL과 비교(2025-05-04~2026-05-08, 370일) | 척도 보정한 일 변화 SD 비(RunPulse/비율 ÷ Intervals) 0.9~1.2 (현행 2.06, PMC v2 재현 1.06), 상관 ≥0.84 |
| V4 | 증분 vs 전체 재계산 | 최근 30일 CTL 차 ≤0.1 |
| V5 | 그룹당 RunPulse activity 행 수 | 모든 그룹 1 (현행 396개 그룹이 2~3) |
| V6 | 사본 간 편차 검사(신규 consistency) | 0건 |
| V7 | UTRS 하루 고정 | 같은 날 09:00·21:00 API 값 동일. 9/22 HRV 성분 ≤5 |
| V8 | 분해 v2 | `race_pred_marathon_sec` evidence.range = 12360/14566, confidence 0.36, limiting 4개, signals 활동 1010·13420 |
| V9 | 매트릭스 | days=28과 84의 pairs_n이 다름. 수영 제외. training_load 행에 Intervals 셀 존재 |
| V10 | `python3 scripts/check_data_consistency.py`, `python3 -m pytest tests/`, `python3 scripts/check_docs.py` | 전부 통과 |

**R4 반영·기록**
- 운영 재계산은 스테이징 통과 후 동일 명령으로 실행한다. 실패 시 R0 백업 파일로 되돌린다(버전 문자열로 전후 구분 가능).
- `v0.3/data/decisions.md`에 C1~C6 결정과 전후 비교표를 기록한다. `python3 scripts/gen_metric_dictionary.py`로 메트릭 사전을 재생성한다.
- CTL·TSB·ACWR·UTRS·CIRS 추세에 `events: algo_change`("계산 방식 변경: PMC v2")를 넣어 전후 단절을 사용자에게 알린다.
- Intervals daily CTL/ATL 인제스트(5/8 이후 중단, F-DATA-12)를 복구하면 V3을 상시 회귀 검사로 돌린다(BACKLOG 후보).

---

## 8. 수용 기준

**정확성**
- [ ] §7.4 V1~V10 전부 통과
- [ ] 목록·상세 헤더·차트 눈금·판독·분해·Today에서 같은 메트릭의 표기가 문자열 단위로 같다(자동 테스트: 52개 slug × 4표면)
- [ ] 원시 초(`13223.0 sec`, `3420.0`) 표시 0건(`raw/` 텍스트 재캡처 grep)
- [ ] 같은 값의 등급이 Today·브라우저·웰니스에서 같다(CIRS·UTRS·TSB·ACWR). 프론트에 밴드 절단값 상수 0개(grep)
- [ ] 모든 메트릭 API `unit` 비어 있지 않음, 또는 `format`이 단위를 정의함(consistency 검사, §C4 "단위 없음")
- [ ] API `status`는 §C7 5단 키 또는 null만 쓴다. 분해 v2에서 `terms`·`sources`가 모두 빈 응답 0건(10 §7.3 계약)
- [ ] 예측 기록 차트·스파크라인: 기록 단축 시 선이 위로 간다

**흐름·반응**
- [ ] 차트 점 탭 → 분해 패널 갱신 ≤300ms(prefetch 적중 시 ≤100ms), `?date=` 반영
- [ ] 값 → 분해 → 원천 활동/웰니스 일자: **2탭**(UTRS·CIRS·TSB·CTL·ACWR·예측에서 성립)
- [ ] 기간 3회 변경 후 뒤로가기 1회 → 이전 화면(브라우저)으로 복귀
- [ ] 브라우저 필터 선택 → 상세 → 뒤로가기 시 필터 유지
- [ ] 탭 하이라이트 ≤100ms, 진행바 150ms 지연, 스켈레톤 ≤300ms(§C5, 10 §8과 같은 기준), 분해 패널 열림 시 CLS 0
- [ ] 웰니스 모든 수치 카드가 이동하고, 날짜 이동(‹ ›·스와이프·7일 점)이 된다
- [ ] Library 1단 4화면 모두 서브탭 표시, 형제 이동 1탭

**시각·접근성**
- [ ] y 눈금 3~5개(§C1 nice 값)가 플롯 밖에 있고, 패딩 경계값 라벨 0
- [ ] 모바일 차트: 탭 후 손을 떼도 판독·분해 선택일 유지(§C1, Playwright touch)
- [ ] 177.5→177.6 bpm 스파크라인 진폭 ≤카드 높이의 5%
- [ ] 390px에서 카드 오버플로 0(배지 포함), 모바일 브라우저 스크롤 길이 ≤2,700px(현행 약 5,400px)
- [ ] 칩·← 히트 영역 ≥44px(§C2 DrillChip), `aria-pressed` 적용, 보조 텍스트 대비 ≥4.5:1, 12px 미만 텍스트 0(축 눈금 11px 예외, §C8)
- [ ] 차트 키보드 ←/→·Shift+←/→·Home/End·Esc(§C1), 동적 aria-label
- [ ] `.svelte` 안의 hex 색 0개, 미정의 CSS 변수 0건(§C8 Stylelint)

**설명**
- [ ] 브라우저 카드 100%에 한 줄 정의 또는 해석이 있다
- [ ] 상세 "이 지표는" 4요소: 레지스트리에 `description_short`·`bands`가 있는 메트릭 100%
- [ ] 분해 v2: 가중 합성 지표(UTRS·CIRS·CRS·RRI)는 결론 1줄 + 기여 막대 + 공식·버전, 예측은 evidence

---

## 9. 구현 순서

| 단계 | 내용 | 의존 | 규모 |
|---|---|---|---|
| **S0** | 계산 교정 C1·C1-b·C2·C3·C6 + 단위 테스트 + 스테이징 재계산(R0~R3) | 10-today F-DATA-02(TRIMP)와 한 묶음 | L |
| **S1** | 표시 메타 확장 — 문구(`metric_labels.py`: name_ko·abbr, 이후 description_short·action_hint, daily 84개 우선)·숫자 규칙(`metric_display.py`: format·decimal_places·min_span)·등급(`bands.py`) + 일관성 테스트 + API (a)(b) + `formatMetric` + 프론트 밴드 제거 | S0(TSB 밴드가 PMC v2 전제), 10 S1(§C4 포맷 함수·§C7·§C8 토큰) | M |
| **S2** | `TrendChart`·`Sparkline`을 §C1 ChartScrub 코어로 이관 + 이 탭 확장(§5) | S1, 10 S4(ChartScrub 코어) | M |
| **S3** | explainer(UTRS·CIRS·예측·PMC) + 인라인 `BreakdownPanel`·`ContributionBars`·`PredictionEvidence` + 상세 8/4 레이아웃·`?date=`·"이 지표는" | S1, S2, 10 S2(분해 v2 API·`BreakdownView`). 분해 API는 10 S2와 한 구현이다 | L |
| **S4** | Library `+layout`(서브탭·브레드크럼), 브라우저 검색·URL 필터·내 지표·카테고리 재편·배지·그리드, 기간 replace | S1 | M |
| **S5** | 웰니스 `/:date` + API (d) + 기준선 카드·수면 단계·small multiples | S1, S2 | M |
| **S6** | C4 매트릭스 재구축 + API (e)(f) + 그룹 상세 라우트 + 표 규격 | S0(C3) | M |
| **S7** | 접근성 점검, §C5 스켈레톤 적용 확인, 운영 재계산(R4), 문서·DECISIONS(전후 비교표) | S0~S6. 토큰·폰트·스켈레톤 프리미티브 자체는 10 S1 | S |

S0이 끝나기 전에는 S1의 등급 밴드를 배포하지 않는다(τ가 틀린 TSB에 관례 밴드를 입히면 판정이 더 틀어진다). S4는 S1 직후 병행할 수 있다.

---

## 10. 발견 → 설계 추적표

| 발견 | 설계 위치 | 상태 |
|---|---|---|
| F-DATA-01 PMC τ 절반·49일 절단 | §7.3 C1, §7.4 V1~V4 | 반영(α = `1/τ`, D1 확정) |
| F-DATA-02 TSB·UTRS 등급 밴드 | §4.4(10 §4 TSB 밴드·§C7), S1 | 반영 |
| F-DATA-03 매트릭스 다른 활동·수영 비교, 기간 무의미 | §7.3 C4, §7.2(e), V9 | 반영 |
| F-DATA-04 사본별 RunPulse 값 불일치 | §7.3 C3, V5·V6 | 반영 |
| F-DATA-05 그룹 정의 오류·단위 없음 | §7.3 C4-5, §2.5 | 반영 |
| F-DATA-06 예측 분해 빈 배열·과정밀 | §7.3 C5, §7.2(c) evidence, §4.1 race_time, §2.3 | 반영 |
| F-DATA-07 UTRS HRV 절대 척도·당일 변동 | §7.3 C6, V7 | 반영(BB 이중 계산은 보류 — 99-summary D7 결정 대기) |
| F-DATA-08 부하 신호 7개 판정 충돌, CIRS 포화·대칭 | §2.2 부하 카테고리 대표 2개+세부 접기, §7.3 C2 | 부분 반영: 통합 판정 한 줄은 10 §4·§7.2 `readiness_decision(date)` 결과를 브라우저 부하 섹션 머리에 그대로 표시한다(10 S3 이후, 이 탭 S4). ACWR 정의 충돌은 §11 |
| F-DATA-09 핵심 지표 구성·심박 카테고리 | §2.2 내 지표 기본값·카테고리 재편 | 반영 |
| F-DATA-10 단위 누락·ramp 일간 | §4.1, §7.3 C1 ramp, §8 unit 검사 | 반영 |
| F-DATA-11 웰니스 기준선·누적 기준 시각·BB | §2.4, §7.2(d) | 반영(Garmin Training Readiness 수집은 BACKLOG 후보로 보류 — 인제스트 범위) |
| F-DATA-12 Intervals CTL 수집 중단·신선도 | §4.5 신선도 표기, §7.4 R4 | 부분 반영: 표시는 반영, 인제스트 복구는 sync 과업으로 보류 |
| F-DATA-13 소수·정밀도 | §4.1(§C4) | 반영 |
| F-UI-01 상세 차트 축 문법 | §5(§C1) | 반영 |
| F-UI-02 스파크라인 min-max 과장·방향 | §5 스파크라인 | 반영 |
| F-UI-03 모바일 배지 넘침·반복 | §4.5(§C6), §2.2 | 반영 |
| F-UI-04 분해 시트 원시 라벨·전폭 | §2.3 인라인 패널, §7.1 BreakdownBody 분리 | 반영 |
| F-UI-05 상세 레이아웃·요약 카드 | §2.3 8/4, §5 크기 | 반영 |
| F-UI-06 의미 밴드·기준선·마커 | §5 밴드·refLines·events | 반영(서버 밴드만 사용 — §1 상충 판단) |
| F-UI-07 웰니스 위계·스파크라인·색 | §2.4, §5 small multiples | 반영 |
| F-UI-08 Provider 표 단위·차이 강조 | §2.5, §7.1 ProviderComparison | 반영 |
| F-UI-09 그리드 리듬·섹션 제목·접기 | §2.2, §7.1 | 반영 |
| F-UI-10 접근성 | §5 접근성(§C1), §8(§C8) | 반영 |
| F-UI-11 영문 제목·단위 괄호 | §4.2 | 반영 |
| F-UI-12 하드코딩 색·로딩 | §5 색(§C7·§C8), §6(§C5) | 반영 |
| F-UI-13 서브탭 바 불일치 | §2.1 | 반영 |
| F-UX-01 목록-상세 포맷 불일치·"피크"=최악 | §4.1, §7.2(b) best/worst, §5 방향 | 반영 |
| F-UX-02 "왜?" 경로 단절 | §2.3, §3(`?date=`·원천 행·Today 칩), §7.2(c) sources | 반영(Today D2의 `추세·과거 보기 →`는 §C3.2 ④에 들어갔다) |
| F-UX-03 분해 단순 나열 | §2.3, §7.2(c) conclusion·contributions, ContributionBars | 반영(what-if는 클라이언트 추정 "추정" 표기로 반영) |
| F-UX-04 설명 경로 없음 | §4.3, MetricTerm | 반영 |
| F-UX-05 CIRS 등급 이원화 | §4.4 서버 SSOT | 반영 |
| F-UX-06 웰니스 무반응·일자 상세 없음 | §2.4, §3, 신규 라우트 | 반영 |
| F-UX-07 Provider 비교 목적·행동 없음 | §2.5, §7.2(e)(f), 그룹 상세 라우트 | 반영([대표 소스 변경]은 쓰기 동작이라 설정 화면 과업으로 보류) |
| F-UX-08 검색·즐겨찾기·URL 필터·숨김 고지 | §2.2, §3 | 반영(데스크톱 좌측 카테고리 목록 포함) |
| F-UX-09 서브탭 소실·막다른 ← | §2.1 | 반영 |
| F-UX-10 기간 push·승계 없음 | §3 replace, 기여 행 date·period 승계 | 반영 |
| F-UX-11 로딩 무피드백·점프 | §6(§C5), §8 | 반영(API 일 단위 캐시는 `02-performance.md` P-3 과업과 공유) |
| F-UX-12 상세 제목 영문 | §4.2 | 반영 |
| F-UX-13 30일 변화 기간 무관·무해석 | §7.2(b) change 선택 기간, §4.4 방향색, §2.3 요약 | 반영 |
| F-UX-14 스파크라인 기간·"변동 없음" 모호 | §5 스파크라인 캡션·문구 분리 | 반영 |
| F-UX-15 모바일 5,398px | §2.2 섹션당 4장+모두 보기, §8 ≤2,700px | 반영(가로 캐러셀은 채택하지 않음 — §1 상충 판단) |

---

## 11. 공통 규격 정합 메모 (10-today/design.md §C 대조, 2026-09-28)

**맞춘 내용** ("10-today 공통 규격과 통일" 표시 4곳과 자체 규격 해소)
| 위치 | 기존 안 | 정합 후 |
|---|---|---|
| 머리말 | 10-today 없음, 최소 기재 + "통일" 표시 | §C1~C8 참조, 고유 규격은 `§Cn 확장`. D1(PMC α = `1/τ`) 명시 |
| §1 상충·§2.3 분해 | "Today·활동 상세는 시트 유지", 공식은 패널 끝에 접힘 | 다른 화면은 §C3.1 D2. 메트릭 상세 인라인 패널은 §C3 확장(같은 `BreakdownView`, ②의 공식 1줄을 기여 행 위로) |
| §1·§4.1 예측 | 1h 이상 항상 `h:mm` + 범위 | §C4: 신뢰 <0.5 `3:40 (3:26–4:03)`, ≥0.5 `h:mm:ss` |
| §2.2 TSB 카드 | `−9 ● 전환` | 10 §4 밴드 라벨 `−9 ● 유지` |
| §2.4 근거 칩 | "10-today 칩 규격" | §C2 DrillChip |
| §3 차트 | 호버/탭 고정, ←/→ | §C1 전체(Shift+←/→, Esc, 해제 3방식). `?date=`는 §C3.3 보기 상태처럼 replace |
| §3 ☆ 토스트 | `고정됨 [취소]` | §C5 `[되돌리기]` 5s |
| §4.1 값 포맷 | 자체 표 9행 | §C4 행 매핑표 + 확장 3개(1시간 미만 예측, 수면 `duration`, 단위 크기) |
| §4.4 등급 | 어휘 5단 고정, TSB `보통(훈련 적응)`·`좋음(전환)`·`주의(디트레이닝)`, 방향색 초록/주황 | §C7 5단 키 + 서버 `status_label`. TSB 밴드는 10 §4 정의(과부하·생산적 부하·유지·신선·휴식 과다). 변화량 색은 `--delta-better/worse`(의미색 차용 금지) |
| §4.5 출처 | `● Garmin` 11px + 3px 색점 | §C6 글자 배지(테두리+글자), 좁은 곳만 `G`. `· 기본`·`추정`·`5/8 이후 없음`은 §C6 확장 |
| §5 차트 | 자체 11행 표, `↑ 빠름`, 밴드 라벨 10px, `--color-series-1..4`·`--color-series-muted`, 빈 데이터 `데이터 수집 중 — {조건}`, 1년 격월 | §C1 참조 + 이 탭 설정. `빠름 ↑`, 밴드 라벨 11px 오른쪽 거터 24px, §C7 `--series-1/2/3`, `데이터 수집 중 (n/필요 일수)` + 행동 링크, 1년 `25.10` |
| §6 로딩 | `animate-pulse bg-surface-2`, 배너, 분해 빈 문구 자체 | §C5(진행바·`Skeleton.svelte` surface-3 shimmer·SWR·접힌 오류 상세), §C3.2 빈 상태 문구 |
| §7.1 컴포넌트 | `MetricBreakdown` 유지 + `BreakdownBody` 분리, `MetricTerm`을 10과 공통으로 표기, `layout.css` series 토큰 | 10의 `DrillHost`·`DrillPanel`·`BreakdownView` 사용, 인라인 `BreakdownPanel`만 추가. `MetricTerm`은 Library 고유. 토큰은 10 S1 |
| §7.2 API | `display_name`, `status{key,label}`(예측 `low_confidence`), `bands{from,to}`, 분해 `?scope_id=` + `contributions/children/inputs`, `wellness` 원천 | 10 §7.3 계약: `name_ko`, 평평한 `status`·`status_label`(§C7 키), 신뢰는 `confidence_label`로 분리, `bands{max}`, `explain=1` + `formula.terms`(`drill` = §C3.3 토큰), `wellness_day`. `conclusion`·`evidence`는 §C3 확장 |
| §7.3 C1 | `1/42`, `1/7`(근거 원문만) | D1 확정 명시, 투영·31 R9도 같은 α. 오늘 잠정값은 10 §7.2 `tsb_live` |
| §8·§9·§10 | 스켈레톤 ≤100ms, S2 "10-today와 동시 확정", S7 토큰 정리 | §C5·10 §8 기준(하이라이트 ≤100ms, 스켈레톤 ≤300ms), §C1·§C8 검사 추가, 의존 10 S1·S2·S4, 추적표 참조 갱신 |

**남긴 §C 확장** (Library 고유, §C와 충돌하지 않음)
- §C1 확장: y 라벨 좌측 거터 치수, 4주 기간 주 경계 x 눈금, 위험 점수 비반전, 이벤트 마커 ▲◆, 3개월 이상 7일 이동평균, small multiples 3패널 1 ChartScrub, 스파크라인 `min_span`, 고정 = 분해 선택일.
- §C3 확장: 인라인 분해 패널 컨테이너, `conclusion`·`evidence`(예측) 필드, 무엇을 바꾸면(추정) 줄, 인라인에서 기여 행 `›` = D3 이동, `/library/wellness?date=` 호환 리다이렉트.
- §C4 확장: 1시간 미만 예측 기록, 수면 `duration`, 단위 글자 크기.
- §C6 확장: `RunPulse 계산 · 기본`, `추정` 배지, 매트릭스 셀 `5/8 이후 없음`, 상세 부제의 버전·계산 시각.

**남은 충돌** (10-today §C 또는 사용자 결정 필요)
1. **차이 색 토큰**: §C7에 `--delta-better/worse`가 없다(20 §11-1, 99-summary D1b와 같은 건). 확정 전까지 변화량은 부호·화살표·라벨로 전달하고 색은 무채색으로 둔다.
2. **수면 시간 포맷**: §C4 시간 행은 `h:mm:ss`/`m:ss`뿐이라 `4h 14m`(수면·누적 시간)에 맞는 행이 없다. §C4에 "누적 시간(수면 등) `4h 14m`" 행 추가를 제안한다. 10 Today B2·B3에서도 수면 길이를 보이면 같은 규칙이 필요하다.
3. ~~**카드 안 스파크라인 스크럽**~~ — **해소(2026-09-28 사용자 확인)**: 목록 카드 스파크라인은 당분간 비인터랙티브 유지(§C1 예외). 이 문서가 제안한 "데스크톱 hover만" 절충안은 구현하지 않음 — 3-7(메트릭 목록 재구성) 때 카드 정렬 문제(아래 참조)와 함께 재검토.
3b. **메트릭 목록 카드 순서** (신규, 2026-09-28 사용자 지적): 카테고리 안 카드가 registry 순서로 고정돼 그날 의미 있게 움직인 지표가 파묻힌다. "핵심 지표" 히어로 섹션(§2.2?)은 있지만 나머지는 전부 동일 시각 비중. 3-7 착수 시 정렬 알고리즘(최근 변화 z-score·상태 비중립 우선) 또는 "오늘 주목할 지표" 알고리즘 섹션을 이 절에 설계할 것. 상세: `99-summary.md §8.5`.
4. **ACWR 정의**: 이 문서 C2는 PMC와 분리한 EWMA 7/28, 현행 `acwr.py`와 31 R9는 `ATL/CTL`(7/42), 10 §7.2는 "EWMA `2/(N+1)` 유지"라고만 적었다. D1로 ATL/CTL의 α가 `1/τ`로 바뀌므로, `ATL/CTL`을 유지하면 ACWR 값도 함께 바뀐다. 10 §7.2와 같은 ADR(S0)에서 정의를 하나로 정해야 한다. 권장은 이 문서 C2(`acwr_ewma_v2`).
5. **포맷 함수 이름**: 10 §7.1은 `formatSigned`·`formatPrediction`·`formatDateKo`·`formatByUnit`, 이 문서는 진입점 `formatMetric(meta, v)`다. 이 문서는 `formatMetric`을 registry `format`으로 10의 함수를 고르는 디스패처로 정했다. 10 §7.1에 `formatMetric`을 공용 진입점으로 추가해야 한다.
6. **와이어프레임 기호**: `🔍 ☆ ★ ⓘ ▸ ▾`는 §C8 아이콘 자리 표시다. `search`·`star`(고정)·`source-primary`(★, 99-summary D1e)·`info`는 §C8 아이콘 목록에 없어 추가가 필요하다.
7. **RRI 등급 SSOT 미등재** (신규, 2026-09-28 — 2-5 분해 v2에 RRI explainer 추가하며 발견): `RRICalculator.ranges`(insufficient/building/ready/peak)가 1-2 "등급 SSOT" 작업(`bands.py`) 이관 대상에서 빠져 있어, RRI는 지금 앱 전체에서 status/label 없이 값만 표시된다(다른 메트릭은 전부 `bands.py` 경유). `bands.py`에 `rri` 항목 추가 + `ranges` 제거는 SSOT 파일 변경이라 `check_docs.py` 영향 범위 확인이 먼저 필요 — 이번 작업 범위 밖이라 고치지 않고 기록만 함.
8. **표시 이름 출처 변경** (신규, 2026-10-03): §4.2가 출처를 registry `display_name_ko`에서 `metric_labels.py`로 바꿨다. 10 §4 "용어"(사전은 registry `display_name_ko`)와 10 §7.2 등급 SSOT 행(`metric_registry`에 `display_name_ko`)은 아직 옛 표기다. 10 문서 갱신과 DECISIONS ADR 기록은 사용자 승인 후 한다.
