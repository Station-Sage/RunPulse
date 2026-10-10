# 2026-10 UX 검토 06 — Coach 대화 (/coach, /coach/[threadId], /coach/new)

범위: /coach, /coach/[threadId], /coach/new 및 components/coach/(ChatComposer, MessageBlock, EvidenceRow, DegradedBanner, StreamStatus, EngineLine, EngineSheet, ScopeSheet), ChatBody, QuickInput, EvidenceQuote, MetricTerm prefill. plan/ 제외. Coach 컨텍스트 패널·LLM 연동은 보류 상태라 결함으로 다루지 않음(현재 구현분만).
방법: DB 사본에서만 검증, 외부 호출 없음, 코드 변경 없음. 375px/1280px, DOM 텍스트 추출 기준. LLM provider 함수는 사본 서버에서 차단(호출 시도 4건 모두 차단 로그 확인).
기존 검토와 중복되는 항목은 한 줄로만 언급(D-22 쓰기 API Origin/CSRF 부재, D-01 내부 링크 {base} 누락, 빈 h1, 터치 타깃 44px 미만).

| ID | 화면/카드/항목 | 관점 | 증상 | 재현 | 심각도 |
|----|---------------|------|------|------|--------|
| C-01 | /coach/[id] 사용자 말풍선 | 화면 | 공백 없는 긴 문자열이 말풍선 안에서 줄바꿈되지 않아 페이지가 가로로 넘침(375px에서 scrollWidth 1642 vs 375). 사용자 말풍선이 white-space: normal이라 입력한 줄바꿈도 한 줄로 합쳐짐 | 스레드에 URL 같은 300자 무공백 문자열 전송, 여러 줄 입력 전송 후 확인 | 상 |
| C-02 | POST /coach/threads (initial_message) | 보안/데이터 | initial_message에 문자열이 아닌 값(숫자·객체)을 보내면 api_error 대신 HTML 500 응답. 엔벨로프 계약 위반 | `{"initial_message":123}` POST | 중 |
| C-03 | 전송 범위 동의 다이얼로그 | 접근성 | Esc로 닫히지 않음. 포커스가 다이얼로그 안 "전송" 버튼이 아니라 배경 쪽 BUTTON:전송에 머묾(aria-modal=true인데 포커스 이동·트랩 없음) | 첫 전송 시 다이얼로그 열고 Esc, Tab | 중 |
| C-04 | /coach/[id] 진입 스크롤 | 편의 | 긴 대화를 열면 최신 메시지가 아닌 맨 위가 보임(scrollY 0, 문서 높이 1694). scrollToBottom은 전송·라이브 갱신에서만 호출 | 메시지 많은 스레드 직접 진입 | 중 |
| C-05 | /coach 목록 | 성능/편의 | list_threads에 LIMIT·페이지네이션 없음. 스레드 48개에서 Tab 정지점 64개, "+ 새 대화 시작"과 바로 물어보기 칩이 목록 아래로 밀려 스크롤 필요. 메시지 길이 상한도 없음 | 사본에 스레드 다수 생성 후 /coach | 중 |
| C-06 | 답변 근거 시각(stamp) | 데이터 | answerEvidence.stamp()가 DB UTC 문자열을 시간대 변환 없이 표시. KST 기준 9시간 어긋남(예: "10/10 17:03 계산"은 실제 10/11 02:03 KST) | 근거 시트의 "답변 당시 41.6 (10/10 17:03 계산 · 2.0)" 확인, metric_store.updated_at과 대조 | 중 |
| C-07 | prefill 제안 문구 | 용어 | 조사 미해결 문구가 그대로 노출: "은(는)", "이(가)", "을(를)", "체력 52은(는)" | /coach/new?metric=ctl 등으로 제안 확인 | 하 |
| C-08 | /coach/new prefill 오류 | 편의 | 지표 prefill 오류도 "활동 정보를 불러올 수 없습니다"로 표시(활동 아님). metric만 있고 date 없음, 대문자 metric, 미래 날짜, 미지 metric이 모두 같은 오류로 끝나며 복구 안내 없음. 지표 prefill인데 불필요한 /data/sync-state 호출 발생 | /coach/new?metric=TSB, ?metric=tsb(날짜 없음), ?metric=tsb&date=미래일 | 중 |
| C-09 | /coach/12abc | 데이터 | 경로 파라미터를 parseInt 계열로 읽어 "12abc"가 스레드 12로 열림(안내 문구도 "스레드를 찾을 수 없습니다: 12"). abc는 올바르게 "잘못된 스레드 ID" | /coach/12abc | 하 |
| C-10 | /coach, 오류 화면 | 접근성 | /coach 및 /coach/[bad id] 오류 화면의 h1이 비어 있음(빈 h1 기존 지적과 동일 계열) | /coach, /coach/999 | 하 |
| C-11 | 스레드 제목 | 용어 | _derive_title이 첫 30자 단순 절단: 마크다운이 중간에 잘리고(`<img ... *…`) 줄바꿈→공백 치환으로 연속 공백 발생. 동일 제목은 목록에서만 날짜로 구분되고 제목 자체는 중복 | 마크다운·줄바꿈 포함 첫 메시지로 스레드 생성 | 하 |
| C-12 | ChatComposer | 접근성 | textarea에 aria-label 없음(placeholder만). 빈 입력에서도 "전송" 버튼이 비활성이 아님. 메시지 영역에 role=log 같은 live region 없음(null/assertive 1건뿐). 터치 타깃 44px 미만(전송 36, 칩 26, "AI 설정 ›" 16, "원인 보기 ›" 16 등; 터치 타깃 기존 지적과 동일 계열) | 375px에서 접근성 트리·bbox 측정 | 중 |
| C-13 | 엔진 표기 문구 | 용어 | 같은 상태가 화면마다 다른 말: "규칙 답변(이전 방식)" / "규칙 답변 (AI 미설정)" / "기본 규칙 답변". "TSB(신선도)" / "폼(TSB)" / "폼" 혼용. "AI 설정" / "설정 > AI" / "전송 범위" 혼용. 레거시 답변은 Claude·ChatGPT API 키 입력을 안내하지만 앱은 Gemini+동의 방식. 레거시 본문에 영문 "moderate" 노출 | /coach/1(레거시 답변), 신규 규칙 답변, 동의 후 폴백 답변 비교 | 중 |
| C-14 | 폴백 배지 사유 | 데이터 | AI 호출 실패 사유가 항상 "네트워크 오류"로 표시(LLM 차단 환경이라 실제 원인과 무관하게 동일). 규칙 답변이 질문 내용("동의 테스트", "느린 테스트")을 무시하고 같은 TSB 문장·같은 후속 칩 3개를 반복 | 동의 후 전송 3회, 답변 비교 | 중 |
| C-15 | /coach 목록 행 시간 | 용어 | 한 행에 상대 시간 둘: "15일 전 대화 · 당시 기준"과 "2주 전". 어느 쪽이 갱신 시각인지 불명확 | 오래된 스레드가 있는 목록 | 하 |
| C-16 | 목록 정렬 | 데이터 | ORDER BY t.updated_at DESC 단일 키. 같은 초에 갱신된 스레드는 순서 불안정(보조 키 id 없음) | 같은 초에 스레드 2개 생성 후 목록 | 하 |
| C-17 | 동의 기본값 | 보안 | 동의 한 번으로 fallback_enabled=true 기본이라 두 번째 공급자(groq)로도 질문과 러닝 데이터가 전송됨. 다이얼로그 문구는 "gemini 서버로 전송"만 강조하고 폴백 토글은 하단 작은 항목. exclude_notes 기본 false(체크인 메모 포함) | 동의 다이얼로그 문구와 PUT /coach/consent 페이로드 확인 | 중 |
| C-18 | 쓰기 API (threads, messages, consent) | 보안 | Origin/CSRF 검사 없음 | D-22 동일 | 중 |

## 검증했고 문제 없음

- 빈 입력·공백 입력: API가 거부, UI도 전송하지 않음.
- HTML/마크다운 주입(`<img onerror>`, `javascript:` 링크, `**b**`): 텍스트로 렌더, 스크립트 실행 없음.
- 동일 client_msg_id 재전송: 멱등(중복 메시지 없음).
- 존재하지 않는 스레드: 404와 "대화를 찾을 수 없습니다" + "← Coach로" 복귀 링크 정상. 0, -1, abc도 오류 화면(C-09 제외).
- 전송 실패: 입력 내용 보존, "전송 실패 · 다시 보내기 · 수정" 노출, 재시도 시 같은 client_msg_id 사용.
- 느린 응답(5초 지연): 중복 Enter에도 요청 1건, 완료 후 입력창 정상 복귀.
- 근거/prefill 수치 대조: TSB 41.6, CTL 52.0, ATL 10.4, 활동 1 4.93km·5:27/km·디커플링 1.7·TSB 15.5가 DB 사본(metric_store)과 일치. 근거 시트의 7일/90일 평균, 신선도 구간 표시 정상.
- 375px/1280px 모두 오류 화면과 /coach/new에서 가로 넘침 없음(C-01 제외).
- 외부 LLM 호출: 차단 로그에 시도 4건, 실제 전송 0건.
- 참고: 사본의 TSB +41.6 "휴식 과다"는 사본 데이터(bg_sync) 산물이라 결함으로 보지 않음.

## 미검증

- EngineSheet와 "원인 보기" 시트의 내용·동작, "AI로 다시 생성" 클릭 동작: LLM 차단 환경이라 실제 재생성 경로 미확인.
- 실제 LLM 답변(ok 상태) 렌더, SSE 스트리밍 중 중간 상태 장시간 관찰.
- 느리거나 중단된 GET(/coach, /coach/[id]) 로딩·오류 상태.
- 실제 모바일 키보드 동작(가상 키보드로 인한 입력창 가림, viewport 변화).
- 다른 사용자의 스레드 접근 차단: 단일 사용자 사본이라 코드 읽기로만 확인(스레드 조회에 소유자 조건 여부는 실측 못함).
- 1280px 시각 배치 정밀 확인: DOM 텍스트와 scrollWidth만 확인, 스크린샷 판독 생략.
- Coach 컨텍스트 패널(보류).
