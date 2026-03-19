# CLAUDE.md - RunPulse

## 필수 읽기 (세션 시작 시 반드시)
1. .ai/todo.md - 현재 작업 목록, 진행 상태
2. .ai/architecture.md - 시스템 구조, 데이터 흐름, AI 코치 플로우
3. .ai/decisions.md - 설계 결정 기록 (D1~D18)

필요 시 참조: .ai/data-sources.md, .ai/roadmap.md, .ai/files.md

## 프로젝트 개요
- 이름: RunPulse - 개인 러닝 코치 에이전트
- 목적: Garmin, Strava, Intervals.icu, Runalyze 4개 소스의 러닝/건강 데이터를 통합 분석하고, AI 코치가 훈련 계획을 추천하며, 가민 워치에 자동 등록
- 저장소: https://github.com/Station-Sage/RunPulse
- 실행 환경: Android Termux, Python 3.11+, SQLite3, 파일 기반 저장
- AI 분석: Genspark AI Chat (무료) 기본, 다른 AI(ChatGPT, Claude, DeepSeek) 교체 가능
- 비용: 전액 무료

## 핵심 아키텍처 요약
- Phase 1-2: DB + 4소스 동기화 (완료)
- Phase 3: 분석 10개 모듈 (compare, trends, recovery, weekly_score, efficiency, zones, activity_deep, race_readiness, report, CLI)
- Phase 4/4-1/4-2: 목표관리 + AI코치(브리핑/칩/파싱) + 가민워크아웃
- Phase 5: 웹 대시보드 (대시보드탭, AI코치탭, 훈련계획탭)

## 기술 스택
- Python 3.11+, SQLite3 (running.db)
- garminconnect[workout] (비공식, Typed Workout 모델 포함)
- httpx (Strava/Intervals/Runalyze API)
- gpxpy, fitparse (GPX/FIT 파싱)
- Flask (웹 대시보드)

## 브랜치 전략
- main: 안정 릴리스 전용, 보호됨
- dev: 개발 기본 브랜치, 모든 PR은 dev로
- claude/*: Claude Code 작업 브랜치 (dev에서 분기)

## 빌드 및 실행 명령어

    python src/db_setup.py                         # DB 초기화
    python src/sync.py --source all --days 7       # 데이터 동기화
    python src/analyze.py today                    # 오늘 리포트
    python src/analyze.py compare --period week    # 주간 비교
    python src/analyze.py deep --activity-id 123   # 단일 활동 심층 분석
    python src/analyze.py race                     # 레이스 준비도
    python src/analyze.py full --clipboard         # 전체 리포트 클립보드
    python src/plan.py week                        # 이번 주 훈련 계획
    python src/serve.py                            # 웹 대시보드 localhost:8080
    python -m pytest tests/                        # 테스트

## 핵심 규칙
1. 파일 300줄 이하 유지. 초과 시 모듈 분리
2. 모든 외부 API 호출은 src/utils/api.py의 래퍼 함수 사용
3. 비밀 정보(토큰, 비밀번호)는 config.json에 저장. 절대 커밋 금지
4. 숫자 계산은 Python에서 수행. LLM은 해석/서술/계획 생성에만 활용
5. 4개 소스의 중복 활동은 timestamp ±5분 AND distance ±3%로 매칭
6. CLI 출력은 마크다운 형식. --clipboard 옵션으로 termux-clipboard-set 연동
7. 커밋 메시지: conventional commits (feat: fix: docs: refactor: test:)
8. 한국어 주석 허용, 코드와 변수명은 영어
9. 프롬프트 템플릿은 src/ai/prompt_templates/*.txt 에 분리 관리
10. AI 응답 파싱 실패 시 항상 graceful fallback (규칙 기반 등)

## Who Is Claude Code
시니어 Python 엔지니어로서 깔끔하고 테스트 가능한 코드를 작성한다.
작업 전 반드시 plan을 세우고 승인을 요청한다.
불필요한 칭찬이나 장황한 설명 없이 핵심만 전달한다.
파일 생성과 수정은 확인 없이 진행하되, 설계 변경은 반드시 확인한다.
