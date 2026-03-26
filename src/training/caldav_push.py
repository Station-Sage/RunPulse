"""CalDAV 캘린더 연동 — 훈련 계획을 외부 캘린더에 등록.

Google Calendar, 네이버 캘린더, Apple iCloud, Synology 등 CalDAV 지원 서비스에 동작.

설정 (config.json):
  "caldav": {
    "url": "https://caldav.googleapis.com/caldav/v2/user@gmail.com/events/",
    "username": "user@gmail.com",
    "password": "앱 비밀번호"
  }

Google Calendar CalDAV 사용 시:
  - Google 계정 → 보안 → 앱 비밀번호 생성
  - url: https://caldav.googleapis.com/caldav/v2/{email}/events/

네이버 캘린더 CalDAV:
  - url: https://caldav.calendar.naver.com/{user_id}/calendar/
  - 네이버 앱 비밀번호 사용
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


def push_workout_to_caldav(
    config: dict,
    workout: dict,
) -> bool:
    """단일 워크아웃을 CalDAV 캘린더에 이벤트로 등록.

    Args:
        config: 설정 dict (caldav 섹션 필요).
        workout: planned_workouts 행 dict.

    Returns:
        성공 여부.
    """
    caldav_cfg = config.get("caldav", {})
    url = caldav_cfg.get("url", "")
    username = caldav_cfg.get("username", "")
    password = caldav_cfg.get("password", "")

    if not url or not username:
        return False

    wtype = workout.get("workout_type", "easy")
    if wtype == "rest":
        return False

    workout_date = workout.get("date", "")
    dist = workout.get("distance_km")
    pace_min = workout.get("target_pace_min")
    pace_max = workout.get("target_pace_max")

    # 이벤트 제목/설명 생성
    _LABELS = {
        "easy": "이지런", "tempo": "템포런", "threshold": "역치런",
        "interval": "인터벌", "long": "장거리런", "recovery": "회복조깅",
        "race": "레이스",
    }
    summary = f"🏃 RunPulse: {_LABELS.get(wtype, wtype)}"
    if dist:
        summary += f" {dist:.1f}km"

    desc_parts = [f"운동 유형: {_LABELS.get(wtype, wtype)}"]
    if dist:
        desc_parts.append(f"거리: {dist:.1f}km")
    if pace_min and pace_max:
        m1, s1 = divmod(pace_min, 60)
        m2, s2 = divmod(pace_max, 60)
        desc_parts.append(f"목표 페이스: {m1}:{s1:02d}~{m2}:{s2:02d}/km")
    rationale = workout.get("rationale", "")
    if rationale:
        desc_parts.append(f"\n{rationale}")
    description = "\n".join(desc_parts)

    # iCal 이벤트 생성
    uid = f"runpulse-{workout.get('id', workout_date)}-{wtype}@runpulse"
    vcal = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//RunPulse//Training Plan//KO\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTART;VALUE=DATE:{workout_date.replace('-', '')}\r\n"
        f"DTEND;VALUE=DATE:{workout_date.replace('-', '')}\r\n"
        f"SUMMARY:{summary}\r\n"
        f"DESCRIPTION:{description}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    try:
        import caldav
        client = caldav.DAVClient(url=url, username=username, password=password)
        principal = client.principal()
        calendars = principal.calendars()
        if not calendars:
            print("[caldav] 캘린더를 찾을 수 없습니다.")
            return False

        # 첫 번째 캘린더 (또는 config에서 지정)
        cal_name = caldav_cfg.get("calendar_name", "")
        cal = calendars[0]
        if cal_name:
            for c in calendars:
                if c.name == cal_name:
                    cal = c
                    break

        cal.save_event(vcal)
        return True
    except ImportError:
        print("[caldav] caldav 패키지 필요: pip install caldav")
        return False
    except Exception as exc:
        print(f"[caldav] 이벤트 등록 실패: {exc}")
        return False


def push_weekly_plan_to_caldav(
    config: dict,
    conn: sqlite3.Connection,
    week_offset: int = 0,
) -> int:
    """주간 훈련 계획 전체를 CalDAV 캘린더에 등록.

    Returns:
        등록 성공 수.
    """
    from src.training.planner import get_planned_workouts

    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    workouts = get_planned_workouts(conn, week_start)

    if not workouts:
        return 0

    count = 0
    for w in workouts:
        if w.get("workout_type") == "rest":
            continue
        if push_workout_to_caldav(config, w):
            count += 1

    return count


def test_connection(config: dict) -> tuple[bool, str]:
    """CalDAV 연결 테스트.

    Returns:
        (성공 여부, 메시지).
    """
    caldav_cfg = config.get("caldav", {})
    url = caldav_cfg.get("url", "")
    username = caldav_cfg.get("username", "")
    password = caldav_cfg.get("password", "")

    if not url:
        return False, "CalDAV URL이 설정되지 않았습니다."

    try:
        import caldav
        client = caldav.DAVClient(url=url, username=username, password=password)
        principal = client.principal()
        calendars = principal.calendars()
        names = [c.name for c in calendars]
        return True, f"연결 성공! 캘린더 {len(calendars)}개: {', '.join(names)}"
    except ImportError:
        return False, "caldav 패키지 필요: pip install caldav"
    except Exception as exc:
        return False, f"연결 실패: {exc}"
