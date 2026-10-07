# LATER — 장기 아이디어 풀

## Garmin 동기화 개선
- **GARMIN-C**: 공식 Garmin Developer API 적용 — Push/webhook 기반, IP 차단 무관, 멀티유저 지원 가능. Enterprise 신청 필요. (현 A안의 근본 해결책)
- **GARMIN-LOCAL-REUSE**: `garmin_local_sync.py` — tokenstore에 만료되지 않은 OAuth2 토큰(`expires_at > now+300`)이 있으면 로그인 생략하고 바로 VPS 업로드. tokenstore 경로 결정 로직을 `_garmin_login()` → `main()`으로 이동 필요.
- **GARMIN-B**: SSH 역방향 터널 방식 — 로컬 SOCKS5 데몬 + `ssh -R` + `HTTPS_PROXY`. 전체기간 sync, 백그라운드 sync 가능. 상세: `v0.3/data/garmin-ip-block-research.md`

## v0.4+
- **Phase 7**: UI 재설계 (views_activities_table.py → activity_service 전환 포함)
- **[METRIC] shape_10k / shape_half**: 거리별 Race Shape 메트릭 신규 추가. `MarathonShapeCalculator` 방식과 동일하게 daily-scope Calculator 구현 (10K: Midgley 가중치, Half: Schmid 가중치). `render_race_shape_trio` 3거리 카드 복원.
- [ ] React Native 모바일 앱
- [ ] CalDAV 캘린더 연동 + Garmin workout sync
- [ ] ML 기반 TQI/PLTD 메트릭
- [ ] Genspark AI 연동 (manual B-mode + automated A-mode)
- **AI-MCP-SERVER**: RunPulse MCP 서버 구현 — Claude Desktop 등 외부 앱에서 러닝 데이터 조회
- **AI-TOOL-EXPAND**: tool 추가 후보 — get_training_recommendation, get_injury_risk_detail, get_shoe_stats
- **AI-STREAMING**: AI 응답 스트리밍 (SSE) — 체감 응답 속도 개선
- **AI-CONTEXT-SUMMARY**: 장기 대화 요약 저장 — 최근 6개 이력 제한 극복

## 언젠가
- [ ] 다국어 지원
- [ ] 다중 사용자
- [ ] Strava segment 분석

## 콜드 스타트 구현 시 재설계 (2026-10-08 사용자 결정)
Phase 4-5에서 보류한 항목은 현재 설계를 확장하지 않고, 콜드 스타트(첫 사용자 온보딩·신규 계정) 구현 때 다시 설계해서 진행한다.
- **DATA-DISCONNECT-DELETE**: 데이터 삭제 해제(`keep_data:false`) — cascade 인지 소스별 삭제 헬퍼 필요(활동·파생 지표·source_payloads·FK)
- **DATA-GARMIN-CONNECT-V2**: Garmin v2 연결(이메일/비밀번호·토큰 저장·2단계 인증 인증 흐름 재작성). 현재는 기존 `/connect/garmin` 링크
- 관련: ADR-026(v0.3/data/decisions.md), IMPL-PROGRESS Phase 4-5/4-6
