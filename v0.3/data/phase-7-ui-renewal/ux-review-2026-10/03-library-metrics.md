# 03 · 라이브러리 지표 (메트릭·Provider·웰니스·이야기) UX 점검 — 2026-10

범위: `/library/metrics`, `/library/metrics/[slug]`, `/library/providers`, `/library/providers/[group]`, `/library/wellness`, `/library/wellness/[date]`, `/library/story/[period]`.
방법: DB 사본(오늘=2026-10-11) + synth 서버 + Playwright. DOM 텍스트를 API JSON과 코드로 대조. 코드 수정 없음(식별만).
중복 표기: `T-xx`/`A-xx` = 2026-10 다른 파일 동일, `F-xx` = 2026-09/21-library-metrics/data.md 동일 계열.

| ID | 화면/카드/항목 | 관점 | 증상 | 재현 | 심각도 |
|----|---------------|------|------|------|--------|
| M-01 | 이야기 `/library/story/[period]` 주 모드 | 데이터/화면 | 주 모드 전체 고장. API 500 `cannot access local variable 'prev_year'`. UI는 "불러오지 못했어요"+재시도만 반복. 원인: `src/services/story_service.py:191` 주 분기에서 월 분기 변수 `prev_year`(155행) 사용. 같은 분기가 달력 연도와 ISO 주차를 섞어 연말 경계도 오류 | `/library/story/2026-09`에서 "주" 클릭, 또는 `GET /api/v1/library/story/2026-W40` | 상 |
| M-02 | 웰니스 최신값 → UTRS 카드(목록·상세) | 데이터 | 마지막 웰니스가 09-27(14일 전)인데 UTRS 85 "매우 좋음/강도 높은 세션도 가능"을 신선한 값처럼 표시. 입력 1개(폼)뿐, API confidence 0.25(낮음)인데 화면에 신뢰도·경과일 경고 없음. 수면 계열 상세도 stale 안내 없음 (T-03 동일 계열) | `/library/metrics`, `/library/metrics/utrs` | 상 |
| M-03 | 목록 카드·상세 "선택 기간 변화" 퍼센트 | 데이터 | 0 근처/부호 교차 기준값 대비 %가 무의미: TSB ▲708%(목록) vs +196.8%(상세), REC +2420.6%, active_calories +427.5%, skin_temp ▼150%. API change_pct와 부호도 다름: TSB(API −196.8), ramp_rate(−95.5 vs UI +95.5), skin_temp_deviation(−85.7 vs +85.7), heat_model(+15.3 vs −15.3) | `/library/metrics` TSB 카드, `/library/metrics/tsb`, API `/library/metrics/{slug}/trend` 대조 | 상 |
| M-04 | 상세 "피크" 타일 | 데이터 | 항상 최댓값. 낮을수록 좋은/중립 지표에서 최악일을 "피크"로 표시. 마라톤 예측 피크 3:47:04(8/25)는 가장 느린 예측. CIRS·ACWR·resting_hr·sleep_awake 동일. higher_is_better=None인 예측류 포함 | `/library/metrics/marathon_prediction`, `/cirs`, `/resting_hr` | 상 |
| M-05 | 상세 `?date=` 핀 vs 타일 | 데이터 | 차트·분해·MetricAbout은 핀 날짜를 따르나 "현재/변화/피크" 타일은 최신일 값. 웰니스에서 오는 링크가 이 상태를 만듦: 차트 84.0 vs 현재 52.0 | `/library/metrics/sleep_score?date=2026-09-26` | 중 |
| M-06 | 목록·상세 단위 중복 | 용어 | RTTI·marathon_shape·avg_spo2·min_spo2가 "66% %", "−87% %", "98% %"로 단위 이중 표기 (F-DATA-10 계열) | `/library/metrics` 해당 카드, 상세 현재 타일 | 중 |
| M-07 | 상세 설명 부재 | 화면 | 52개 중 25개가 description_short 없음 → 설명·"이 지표는" 영역 없음: training_response, rec, sapi, critical_power, eftp, lt_speed_ref, garmin_ftp, sleep_* 단계, sleep_avg_hr, sleep_body_battery_change, avg/min_spo2, skin_temp_deviation, steps, active_calories, avg/min_respiration_sleep, lthr_self, hrmax_self, hrv_5min_high, lthr_ref, heat_model | `/library/metrics/rec` 등 | 중 |
| M-08 | 상세 sleep_score 등 비-EXPLAIN 슬러그 | 화면 | 출처 배지·분해·MetricAbout 모두 없음. 드릴 시트는 "분해 대신 추세로 볼 수 있어요"만 표시 | `/library/metrics/sleep_score`, "계산 분해 보기" | 중 |
| M-09 | 상세 이름 vs 목록 이름 | 용어 | H1이 영어 풀네임/"약어 (한글)"/한글 혼재, 목록과 불일치: "Unified Training Readiness Score" vs "훈련 준비도", "Body Battery" vs "바디 배터리" (4.2 표시 이름 규격 미적용) | `/library/metrics/utrs` | 중 |
| M-10 | 목록 vs 상세 숫자 형식 | 데이터 | 자릿수 불일치: 52 vs 52.0, TSB 21 vs +21, training_response 12.1 vs 12. 값 반올림: ACWR 0.67→0.7, monotony 1.09→1.1, LSI 0.82→0.8, ramp −0.09→−0.1. 단위 "count" 원문 노출, steps 천단위 구분 없음, "brpm" 전문용어 (F-DATA-13 계열) | `/library/metrics/steps`, `/acwr` | 중 |
| M-11 | UTRS MetricAbout 본문 | 데이터 | 본문 "7일 평균 79.53"(소수 2자리)이 API 마지막 7점 평균 79.34와 불일치, "90일 평균 67.47"은 기준선 평균 67.29와 불일치(창 정의 상이) | `/library/metrics/utrs` | 중 |
| M-12 | UTRS 설명 vs 문서 | 데이터 | UI 가중치/등급 경계(30/50/70/85)가 `v0.2/.ai/metrics.md` PDF 기준(수면.25·HRV.25·TSB.20·RHR.15·일관성.15, 0-40/41-60/61-80/81-100)과 다름. 문서 400행 UI 변형(BB.30…)과도 다름 → 어느 쪽이 기준인지 표기 없음 (F-DATA-02 계열) | `/library/metrics/utrs` 설명 vs metrics.md 224-240, 400행 | 중 |
| M-13 | 목록 Provider 필터 | 편의 | 필터 시 provider=null 지표(sleep_score, sleep_duration, body_battery_high/low, avg_stress, steps, active_calories, hrv_weekly_avg, hrv_last_night, resting_hr)가 모든 필터에서 사라지고 "내 지표" 섹션도 숨김 | `/library/metrics` Garmin 칩 | 중 |
| M-14 | 이야기 월 비교(진행 중 월) | 데이터 | 10월(1~11일)을 9월 전체와 비교: "−70% (이전 173.9)", "횟수 −58%". 부분 vs 전체 기간 비교임을 알리지 않음 | `/library/story/2026-10` | 중 |
| M-15 | 이야기 "위험 최고 ACWR 0.86" | 용어 | 0.86은 안전 구간인데 "위험" 라벨 | `/library/story/2026-09` | 중 |
| M-16 | 이야기 미래 월 | 편의 | 가드 없음: 2026-11 "−100%", › 버튼 무제한 이동. 연 단위 `/story/2026`은 400→404 (월·주 외 형식 안내 없음) | `/library/story/2026-11`, `/library/story/2026` | 중 |
| M-17 | 웰니스 판정 문구 | 데이터 | 2026-05-25에서 "회복 좋음"과 CIRS "높음"(58)이 동시에 표시되어 모순 | `/library/wellness/2026-05-25` | 중 |
| M-18 | 웰니스 날짜 라벨 | 화면 | 연도 없음: 2020-01-01 요청 시 "가까운 기록(10월 1일 (일))" 어느 해인지 모호 (A-07 동일 계열) | `/library/wellness/2020-01-01` | 중 |
| M-19 | Provider 매트릭스 신선도 | 데이터 | Garmin 데이터가 09-27에서 끊겼는데 셀 stale:false. 페어 "Garmin↔RunPulse 9건"(러닝 17건 중). 범례에 Strava 있으나 Strava 열 없음. 그룹 페이지에 "-0%", "0%" 표기 | `/library/providers`, `/library/providers/training_load` | 중 |
| M-20 | Provider `days` 파라미터 | 편의/보안 | 28/56/84 외 API는 INVALID_PARAM인데 UI는 `days=999`를 조용히 4주로 대체, URL은 그대로 | `/library/providers?days=999` | 하 |
| M-21 | 수면 시간 표기 | 용어 | 한 화면에 단계 "57:00"(mm:ss), 합계 "4:14:39", 변화 "−15:21"이 혼재하고 단위 없음. 웰니스 페이지는 "7h 18m" 형식 → 페이지 간 불일치 | `/library/metrics/sleep_duration`, `/library/wellness/2026-09-26` | 중 |
| M-22 | 웰니스 반올림 | 데이터 | "+19m"(실제 20m), "−2h 46m"(실제 2h 47m)처럼 분 단위 버림/반올림 혼용 | `/library/wellness/2026-09-26` 비교 칩 | 하 |
| M-23 | 웰니스 미래 날짜 | 편의 | 미래 날짜가 안내 없이 오늘로 리다이렉트 | `/library/wellness/2030-01-01` | 하 |
| M-24 | 웰니스 `2026-02-30` | 편의 | 존재하지 않는 날짜에 "형식이 올바르지 않아요" 메시지(형식은 맞음) | `/library/wellness/2026-02-30` | 하 |
| M-25 | 상세 `?period=`·`?date=` 오류값 | 편의 | `?period=zzz`, `?date=bad`는 오류 없이 무시(URL 유지). `?date=2030-01-01`은 explain 404 후 "이 날은 분해할 계산 값이 없어요"로 정상 처리 | `/library/metrics/utrs?period=zzz` | 하 |
| M-26 | 차트 대체 텍스트 | 접근성 | 웰니스 30일 추세 SVG 6개와 상세 TrendChart가 aria-hidden, 텍스트 대안 없음(스크린리더에 값 전달 불가) | `/library/wellness/2026-09-26`, 상세 차트 | 하 |
| M-27 | 터치 대상 크기 | 접근성 | 375px에서 목록 칩 약 24px·별 28px, 기간 버튼 24px 높이, 상세 ⓘ 20x20, 웰니스 "수면" 링크 22x16·이전/다음 36x36, 이야기 월/주 토글 28px (T-12 동일 계열) | 375px 각 화면 | 하 |
| M-28 | aria-pressed 불일치 | 접근성 | 목록 카테고리/Provider 칩, 상세 기간 버튼에는 없고 Provider 4/8/12주·이야기 월/주에는 있음 (T-19 계열) | 각 화면 DOM | 하 |
| M-29 | 목록 검색 | 편의 | 동의어 없음: "VO2", "회복" 검색 결과 0건. 빈 결과 안내만 | `/library/metrics` 검색창 | 하 |
| M-30 | 칩 전환·핀 | 편의 | 칩 변경이 replaceState라 뒤로가기 시 목록을 벗어남. 핀은 localStorage뿐(기기 간 미동기) | 칩 클릭 후 Back | 하 |
| M-31 | 문구 | 용어 | "폼이(가)" 조사 템플릿 노출, recompute_note가 같은 문장을 두 번 반복 | `/library/metrics/utrs` | 하 |
| M-32 | 차트 y축 | 화면 | 눈금이 비정형(92.0, 63.6, 35.2), 밴드 라벨 "–30"/"85–" (T-10 동일 계열) | `/library/metrics/utrs` | 하 |
| M-33 | 상세 로딩 상태 | 체감 성능 | 목록 응답 2.5초 지연 주입 시 스켈레톤/진행 표시 없이 칩 줄만 보이고 카드 영역은 비어 있음(본문 텍스트 기준) | route delay 후 `/library/metrics` | 하 |

## 확인 완료 체크리스트 (문제 없음 포함)

- 지표 목록: 52개 값이 API와 일치, `?category=` 딥링크 정상, 검색 입력 인젝션 안전. 문제: M-03, 06, 10, 13, 29, 30, 33.
- 지표 상세: 52개 슬러그 현재값·피크 API 일치(M-04는 의미 문제). 잘못된 slug/period/date 처리 확인(slug는 "메트릭 데이터를 불러올 수 없습니다"+복귀 링크, 텍스트만 에코, 인젝션 없음). trend API abort 시 오류 안내+복귀 링크 정상.
- 드릴 시트: Esc 닫기, aria-modal, URL `&drill=` 정상.
- 375px 가로 넘침 없음: 상세, Provider(표는 컨테이너 내부 스크롤+첫 열 고정), 웰니스, 이야기.
- 정상 페이지 콘솔/HTTP 오류 없음.
- 웰니스: 09-26 값이 API와 일치(수면 26280초=7h18m, 단계, BB). 이전/다음 끝에서 비활성, 주 스트립, Tab 순서 양호. 잘못된 날짜는 오류+복귀 링크. 기록 없는 날(10-11)은 "웰니스 기록이 없어요/가까운 기록으로 이동". 문제: M-17, 18, 21~24, 26.
- Provider: 그룹 페이지 페어 목록 렌더, 비교 불가 그룹 안내 문구 정상, 잘못된 그룹 오류 처리 정상. 문제: M-19, 20.
- 이야기: 2026-08/09 월 페이지 정상(마일스톤·세션 링크·복사 버튼). 문제: M-01, 14~16.
- 중복: 2026-09 리뷰의 F-DATA-02/10/12/13과 계열이 같은 항목은 위 표에 병기했고, 이번 점검은 구현 후 현재 상태 기준.

## 미검증 항목

- 색 대비 수치 계산(WCAG)은 시간상 하지 못함. 키보드 외 스크린리더 실동작 미확인.
- 로딩 스크린샷(m_loading.png)과 375px 스크린샷 4장은 저장만 하고 열람하지 않음(텍스트 기준 점검).
- SourceCoverage/Summary, MilestonesPanel/PersonalBests 세부 값의 DB 원천 대조는 이야기 2026-08/09 외 월은 미실시.
- MetricAbout 본문 대 metrics.md 대조는 UTRS만 수행. CIRS·ACWR·RTTI·TSB·REC 등은 미대조.
- 이야기 주 모드는 M-01 때문에 UI 내용 전체 미검증.
- 입력 테스트는 사본에서만 수행(운영 DB 무변경).
