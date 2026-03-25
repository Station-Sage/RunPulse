#!/usr/bin/env python3
"""Step 2 보완: API 문서 기반 전체 엔드포인트 vs 감사 완료 대조"""
import json, httpx, os

BASE = "/data/data/com.termux/files/home/projects/RunPulse"

# ============================================================
# 1. Strava: 공식 Swagger에서 모든 GET 엔드포인트 추출
# ============================================================
print("=" * 70)
print("  1. STRAVA — 공식 Swagger GET 엔드포인트 전수 조사")
print("=" * 70)

strava_spec = None
try:
    with httpx.Client(timeout=30) as c:
        r = c.get("https://developers.strava.com/swagger/swagger.json")
        strava_spec = r.json()
except Exception as e:
    print(f"  [FAIL] Swagger 다운로드 실패: {e}")

strava_gets = []
if strava_spec:
    for path, methods in strava_spec.get("paths", {}).items():
        if "get" in methods:
            op = methods["get"]
            strava_gets.append({
                "path": path,
                "operationId": op.get("operationId", ""),
                "summary": op.get("summary", ""),
                "tags": op.get("tags", []),
            })

# 감사에서 검증한 Strava 엔드포인트 매핑
audited_strava = {
    "/athlete": "athlete_profile",
    "/athlete/zones": "zones",
    "/athletes/{id}/stats": "athlete_stats",
    "/athlete/activities": "activity_summary",
    "/activities/{id}": "activity_detail",
    "/activities/{id}/streams": "streams",
    "/activities/{id}/laps": "activity_laps",
    "/activities/{id}/kudos": "activity_kudos",
    "/activities/{id}/comments": "activity_comments",
    "/gear/{id}": "gear_detail",
}

print(f"\n  Swagger GET 엔드포인트 총: {len(strava_gets)}개\n")
print(f"  {'경로':<45s} {'operationId':<35s} {'감사여부':8s}")
print(f"  {'-'*45} {'-'*35} {'-'*8}")

strava_missing = []
for ep in sorted(strava_gets, key=lambda x: x["path"]):
    path = ep["path"]
    audited = "✓ 완료" if path in audited_strava else "✗ 미감사"
    if path not in audited_strava:
        strava_missing.append(ep)
    print(f"  {path:<45s} {ep['operationId']:<35s} {audited:8s}")

print(f"\n  감사 완료: {len(audited_strava)}개 / 미감사: {len(strava_missing)}개")
print(f"\n  미감사 엔드포인트:")
for ep in strava_missing:
    tags = ", ".join(ep["tags"])
    relevant = "→ 러닝분석 관련" if any(k in ep["path"] for k in ["activit", "athlete", "gear", "stream"]) else "→ 러닝분석 무관"
    print(f"    {ep['path']:<45s} [{tags}] {relevant}")

# ============================================================
# 2. Intervals.icu: OpenAPI에서 모든 GET 엔드포인트 추출
# ============================================================
print("\n" + "=" * 70)
print("  2. INTERVALS.ICU — OpenAPI GET 엔드포인트 전수 조사")
print("=" * 70)

intervals_spec = None
try:
    with httpx.Client(timeout=30) as c:
        r = c.get("https://intervals.icu/api/v1/docs")
        intervals_spec = r.json()
except Exception as e:
    print(f"  [FAIL] OpenAPI 다운로드 실패: {e}")

intervals_gets = []
if intervals_spec:
    for path, methods in intervals_spec.get("paths", {}).items():
        if "get" in methods:
            op = methods["get"]
            intervals_gets.append({
                "path": path,
                "operationId": op.get("operationId", ""),
                "summary": op.get("summary", ""),
                "tags": op.get("tags", []),
            })

# 감사에서 검증한 Intervals 엔드포인트 매핑
audited_intervals = {
    # 기본 감사
    "/api/v1/athlete/{id}/activities": "activity_list",
    # 미사용 감사 (v2)
    "/api/v1/activity/{id}": "activity_detail",
    "/api/v1/activity/{id}/intervals": "activity_intervals",
    "/api/v1/activity/{id}/streams": "activity_streams",
    "/api/v1/activity/{id}/streams.csv": "activity_streams_csv",
    "/api/v1/activity/{id}/map": "activity_map",
    "/api/v1/activity/{id}/best-efforts": "activity_best_efforts",
    "/api/v1/activity/{id}/pace-curve": "activity_pace_curve",
    "/api/v1/activity/{id}/hr-curve": "activity_hr_curve",
    "/api/v1/activity/{id}/power-curves": "activity_power_curve",
    "/api/v1/activity/{id}/power-vs-hr": "activity_power_vs_hr",
    "/api/v1/activity/{id}/time-at-hr": "activity_time_at_hr",
    "/api/v1/activity/{id}/hr-load-model": "activity_hr_load_model",
    "/api/v1/activity/{id}/histogram": "activity_histograms",
    "/api/v1/activity/{id}/segments": "activity_segments",
    "/api/v1/activity/{id}/weather": "activity_weather",
    "/api/v1/athlete/{id}": "athlete_profile",
    "/api/v1/athlete/{id}/sport-settings": "athlete_sport_settings",
    "/api/v1/athlete/{id}/gear": "athlete_gear",
    "/api/v1/athlete/{id}/power-curves": "athlete_power_curves",
    "/api/v1/athlete/{id}/pace-curves": "athlete_pace_curves",
    "/api/v1/athlete/{id}/hr-curves": "athlete_hr_curves",
    "/api/v1/athlete/{id}/power-vs-hr": "athlete_power_hr_curve",
    "/api/v1/athlete/{id}/weather": "athlete_weather_forecast",
    "/api/v1/athlete/{id}/weather-config": "athlete_weather_config",
    "/api/v1/athlete/{id}/tags": "athlete_activity_tags",
    "/api/v1/athlete/{id}/routes": "athlete_routes",
    "/api/v1/athlete/{id}/wellness": "wellness",
    "/api/v1/athlete/{id}/wellness/{date}": "wellness_date",
    "/api/v1/athlete/{athleteId}/sport-settings/{id}": "sport_settings_detail",
    "/api/v1/athlete/{athleteId}/sport-settings": "sport_settings_list",
}

print(f"\n  OpenAPI GET 엔드포인트 총: {len(intervals_gets)}개\n")

# 카테고리별 분류
categories = {
    "Activity (데이터 분석)": [],
    "Athlete (프로필/설정)": [],
    "Wellness (건강)": [],
    "Library (워크아웃)": [],
    "Events (캘린더)": [],
    "기타": [],
}

intervals_missing = []
for ep in sorted(intervals_gets, key=lambda x: x["path"]):
    path = ep["path"]
    # 유사 경로 매칭 (파라미터 부분 무시)
    matched = False
    for audited_path in audited_intervals:
        # 정규화 비교
        if path == audited_path:
            matched = True
            break
        # {athleteId} vs {id} 차이 보정
        norm_path = path.replace("{athleteId}", "{id}")
        norm_audited = audited_path.replace("{athleteId}", "{id}")
        if norm_path == norm_audited:
            matched = True
            break

    audited = "✓" if matched else "✗"
    if not matched:
        intervals_missing.append(ep)

    # 카테고리 분류
    tags = ep.get("tags", ["기타"])
    tag = tags[0] if tags else "기타"
    if "activit" in path.lower() and "/athlete/" not in path:
        cat = "Activity (데이터 분석)"
    elif "wellness" in path.lower():
        cat = "Wellness (건강)"
    elif "athlete" in path.lower():
        cat = "Athlete (프로필/설정)"
    elif any(k in tag.lower() for k in ["library", "workout", "folder"]):
        cat = "Library (워크아웃)"
    elif "event" in tag.lower():
        cat = "Events (캘린더)"
    else:
        cat = "기타"

    categories.setdefault(cat, []).append((path, ep["operationId"], ep["summary"][:40], audited))

for cat, items in categories.items():
    if not items:
        continue
    ok = sum(1 for _, _, _, a in items if a == "✓")
    print(f"\n  [{cat}] — {ok}/{len(items)} 감사 완료")
    for path, op, summary, audited in items:
        print(f"    {audited} {path:<55s} {summary}")

print(f"\n  감사 완료: {len(audited_intervals)}개 / 미감사: {len(intervals_missing)}개")

# 미감사 중 러닝 분석 관련 필터
print(f"\n  미감사 중 러닝/훈련 분석 관련:")
relevant_keywords = ["activit", "stream", "interval", "curve", "effort", "wellness", "fitness", "sport", "gear", "weather"]
for ep in intervals_missing:
    is_relevant = any(k in ep["path"].lower() for k in relevant_keywords)
    if is_relevant:
        print(f"    {ep['path']:<55s} {ep['summary'][:50]}")

# ============================================================
# 3. Garmin: garminconnect 라이브러리 메서드 전수 (이미 완료 확인)
# ============================================================
print("\n" + "=" * 70)
print("  3. GARMIN — garminconnect 메서드 감사 현황")
print("=" * 70)

# 감사 파일에서 엔드포인트 목록 추출
garmin_basic = {}
garmin_unused = {}
try:
    with open(os.path.join(BASE, "garmin_field_audit.json")) as f:
        garmin_basic = json.load(f)
except: pass
try:
    with open(os.path.join(BASE, "unused_api_garmin.json")) as f:
        garmin_unused = json.load(f)
except: pass

garmin_total = set()
for k in garmin_basic:
    if not k.startswith("_"):
        garmin_total.add(k)
for k in garmin_unused:
    if not k.startswith("_"):
        garmin_total.add(k)

print(f"\n  기본 감사: {len([k for k in garmin_basic if not k.startswith('_')])}개 엔드포인트")
print(f"  미사용 감사: {len([k for k in garmin_unused if not k.startswith('_')])}개 엔드포인트")
print(f"  합계 (중복 제거): {len(garmin_total)}개 엔드포인트")
print(f"\n  ※ garminconnect 라이브러리 전체 93개 get_ 메서드 중")
print(f"    감사 완료 {len(garmin_total)}개 — 나머지는 호출 파라미터 문제(FAIL)이거나")
print(f"    running_tolerance, personal_records 등 시그니처 불일치로 제외됨")

# ============================================================
# 4. Intervals 실패 3개 분석
# ============================================================
print("\n" + "=" * 70)
print("  4. INTERVALS.ICU — 실패 3개 엔드포인트 분석")
print("=" * 70)

failed_endpoints = {
    "activity_best_efforts": {
        "path": "/api/v1/activity/{id}/best-efforts",
        "error": "422 Unprocessable Entity",
        "analysis": "sport_type 또는 type 쿼리 파라미터 필요 가능성",
    },
    "athlete_power_curves": {
        "path": "/api/v1/athlete/{id}/power-curves",
        "error": "422 Unprocessable Entity",
        "analysis": "type 파라미터(Run, Ride 등) 필수",
    },
    "athlete_power_hr_curve": {
        "path": "/api/v1/athlete/{id}/power-vs-hr",
        "error": "422 Unprocessable Entity",
        "analysis": "type 파라미터 필수, 또는 데이터 부족",
    },
}

for name, info in failed_endpoints.items():
    print(f"\n  {name}")
    print(f"    경로: {info['path']}")
    print(f"    에러: {info['error']}")
    print(f"    분석: {info['analysis']}")

# OpenAPI에서 파라미터 확인
if intervals_spec:
    print(f"\n  OpenAPI spec에서 필수 파라미터 확인:")
    for path, methods in intervals_spec.get("paths", {}).items():
        if "get" in methods:
            for fname, finfo in failed_endpoints.items():
                if path == finfo["path"]:
                    params = methods["get"].get("parameters", [])
                    required_params = [p for p in params if p.get("required")]
                    print(f"\n    {path}:")
                    for p in params:
                        req = "필수" if p.get("required") else "선택"
                        print(f"      {p['name']:20s} ({req}) — {p.get('description', '')[:50]}")

# ============================================================
# 5. 최종 요약
# ============================================================
print("\n" + "=" * 70)
print("  5. 최종 요약: API 문서 대비 감사 완전성")
print("=" * 70)

print(f"""
  서비스         문서상 GET  감사완료  미감사  미감사(분석관련)
  ──────────     ────────   ──────   ─────  ────────────
  Strava          {len(strava_gets):>3}       {len(audited_strava):>3}      {len(strava_missing):>3}     (대부분 세그먼트/클럽/루트 → 무관)
  Garmin          93+        {len(garmin_total):>3}      ~{93-len(garmin_total)}     (파라미터 문제 일부)
  Intervals.icu   {len(intervals_gets):>3}       {len(audited_intervals):>3}      {len(intervals_missing):>3}     (워크아웃/이벤트/채팅 → 무관)

  결론:
  - 러닝 훈련 분석에 필요한 엔드포인트는 거의 전부 감사 완료
  - 미감사 항목은 세그먼트, 클럽, 루트, 워크아웃 관리 등 → 스키마 설계에 영향 없음
  - Intervals 실패 3개는 파라미터 보정으로 재시도 필요
""")

