"""Phase 3 동기화 오케스트레이터.

API 호출 → raw 저장 → 추출 → DB 적재.
비즈니스 로직은 extractor에, sync는 배관(plumbing)만 담당.
RateLimiter로 소스별 속도 제한. SyncResult로 결과 집계.

진입점: orchestrator.full_sync()
개별 소스: garmin_activity_sync.sync(), strava_activity_sync.sync() 등.

설계 문서: v0.3/data/phase-3.md
의존: src/sync/extractors/, src/utils/db_helpers.py, src/utils/rate_limiter.py
주의: Garmin은 rate-limit 감지 후 동적 대기 필요
"""
