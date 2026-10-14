"""교차 소스 시간대 추정 — 다른 소스의 같은 활동에서 UTC 오프셋을 빌린다 (TZ T2, ADR-052).

Strava CSV 는 UTC 만 주므로, Garmin/intervals/Runalyze 가 이미 가진 같은 활동의 현지 시각에서
`offset = local - utc` 를 구해 대상의 현지 벽시계를 만든다 (피어의 local 을 그대로 복사하지 않음).
"""
from __future__ import annotations

import bisect
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.utils.dedup import _SOURCE_PRIORITY, distance_matches

PEER_TOLERANCE_SEC = 60
_STEP_SEC = 900
_ROUND_ERR_SEC = 120
_MIN_OFFSET = -12 * 3600
_MAX_OFFSET = 14 * 3600


@dataclass(frozen=True)
class PeerTime:
    source: str
    source_id: str
    utc: datetime | None
    local: datetime | None
    distance_m: float | None
    grade: str  # "direct" | "derived"


@dataclass
class PeerMatch:
    offset_sec: int
    grade: str
    source: str
    source_id: str
    delta_sec: float
    conflicts: list[dict] = field(default_factory=list)


def _dt(s) -> datetime | None:
    """ISO 문자열 → naive datetime (오프셋 접미사는 무시). 파싱 실패 시 None."""
    if not s or not isinstance(s, str):
        return None
    t = s.strip().replace("Z", "").replace(" ", "T")
    for sep in ("+", "-"):
        i = t.rfind(sep)
        if i > 10:
            t = t[:i]
    try:
        return datetime.fromisoformat(t[:19])
    except ValueError:
        return None


def _has_offset(s) -> bool:
    if not isinstance(s, str):
        return False
    t = s.strip()
    return t.endswith("Z") or (len(t) > 19 and t[19] in "+-")


def _num(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _read_garmin(sid: str, p: dict) -> PeerTime | None:
    utc, local = _dt(p.get("startTimeGMT")), _dt(p.get("startTimeLocal"))
    if not (utc and local):
        return None
    return PeerTime("garmin", sid, utc, local, _num(p.get("distance")), "direct")


def _read_intervals(sid: str, p: dict) -> PeerTime | None:
    utc, local = _dt(p.get("start_date")), _dt(p.get("start_date_local"))
    if not (utc and local):
        return None
    return PeerTime("intervals", sid, utc, local, _num(p.get("distance")), "direct")


def _read_runalyze(sid: str, p: dict) -> PeerTime | None:
    raw = p.get("datetime") or p.get("start_time")
    dt = _dt(raw)
    if not dt:
        return None
    km = _num(p.get("distance"))
    dist = km * 1000 if km is not None else None
    if _has_offset(raw):
        # 오프셋 접미사가 있으면 접미사 앞이 벽시계, 접미사로 UTC 를 복원
        s = raw.strip()
        if s.endswith("Z"):
            utc = dt
        else:
            sign = 1 if s[19] == "+" else -1
            hh, mm = s[20:].replace(":", "")[:2], s[20:].replace(":", "")[2:4] or "00"
            utc = dt - sign * timedelta(hours=int(hh), minutes=int(mm))
        return PeerTime("runalyze", sid, utc, dt, dist, "direct")
    return PeerTime("runalyze", sid, None, dt, dist, "derived")


_PEER_READERS = {"garmin": _read_garmin, "intervals": _read_intervals, "runalyze": _read_runalyze}


def _offset_of(utc: datetime, local: datetime) -> int | None:
    raw = (local - utc).total_seconds()
    snapped = round(raw / _STEP_SEC) * _STEP_SEC
    if abs(raw - snapped) > _ROUND_ERR_SEC or not _MIN_OFFSET <= snapped <= _MAX_OFFSET:
        return None
    return int(snapped)


def _dist_ok(a: float | None, b: float | None) -> bool:
    return a is None or b is None or distance_matches(a, b)


class PeerTzIndex:
    """다른 소스 활동의 (UTC, 현지) 시각 색인. 조회는 bisect."""

    def __init__(self, direct: list[PeerTime], derived: list[PeerTime]):
        self._direct = sorted(direct, key=lambda p: p.utc)
        self._direct_keys = [p.utc for p in self._direct]
        self._derived = derived
        self._extra: list[PeerTime] = []  # 같은 배치의 확정 Strava 행 (이웃 차용 전용)

    def add_confirmed(self, pt: PeerTime) -> None:
        """이웃 차용용 확정 지점 추가 (직접 매칭에는 쓰이지 않음)."""
        self._extra.append(pt)

    @classmethod
    def build(cls, conn: sqlite3.Connection, exclude_sources: tuple[str, ...] = ("strava",)) -> "PeerTzIndex":
        direct: list[PeerTime] = []
        derived: list[PeerTime] = []
        for source, reader in _PEER_READERS.items():
            if source in exclude_sources:
                continue
            rows = conn.execute(
                "SELECT entity_id, payload FROM source_payloads"
                " WHERE source = ? AND entity_type = 'activity_summary'", (source,),
            ).fetchall()
            for sid, payload in rows:
                try:
                    pt = reader(str(sid), json.loads(payload))
                except (ValueError, TypeError, AttributeError):
                    continue
                if pt is None:
                    continue
                (direct if pt.grade == "direct" and pt.utc else derived).append(pt)
        return cls(direct, derived)

    def _direct_candidates(self, utc_target: datetime, distance_m: float | None) -> list[tuple[PeerTime, int, float]]:
        lo = bisect.bisect_left(self._direct_keys, utc_target - timedelta(seconds=PEER_TOLERANCE_SEC))
        hi = bisect.bisect_right(self._direct_keys, utc_target + timedelta(seconds=PEER_TOLERANCE_SEC))
        out = []
        for p in self._direct[lo:hi]:
            off = _offset_of(p.utc, p.local)
            if off is not None and _dist_ok(distance_m, p.distance_m):
                out.append((p, off, abs((p.utc - utc_target).total_seconds())))
        return out

    def _derived_candidates(self, utc_target: datetime, distance_m: float | None) -> list[tuple[PeerTime, int, float]]:
        out = []
        for p in self._derived:
            diff = (p.local - utc_target).total_seconds()
            if not _MIN_OFFSET - PEER_TOLERANCE_SEC <= diff <= _MAX_OFFSET + PEER_TOLERANCE_SEC:
                continue
            off = _offset_of(utc_target, p.local)
            if off is not None and _dist_ok(distance_m, p.distance_m):
                out.append((p, off, abs(diff - off)))
        return out

    @staticmethod
    def _decide(cands: list[tuple[PeerTime, int, float]], grade: str) -> PeerMatch | None:
        if not cands:
            return None
        if grade == "derived" and len(cands) != 1:
            return None  # 추정 후보가 여럿이면 모호 — 채택 안 함
        offsets = {c[1] for c in cands}
        conflicts: list[dict] = []
        if len(offsets) == 1:
            best = min(cands, key=lambda c: c[2])
        else:
            best = min(cands, key=lambda c: (_SOURCE_PRIORITY.get(c[0].source, 99), c[2]))
            conflicts = [{"source": p.source, "source_id": p.source_id, "offset_sec": o} for p, o, _ in cands]
        p, off, delta = best
        return PeerMatch(off, grade, p.source, p.source_id, delta, conflicts)

    def lookup(self, utc_target: datetime, distance_m: float | None = None) -> PeerMatch | None:
        m = self._decide(self._direct_candidates(utc_target, distance_m), "direct")
        if m:
            return m
        return self._decide(self._derived_candidates(utc_target, distance_m), "derived")

    def nearest_confirmed(self, utc_target: datetime) -> tuple[PeerTime | None, PeerTime | None]:
        """UTC 기준 직전·직후의 확정(direct) 피어."""
        pts = sorted([*self._direct, *self._extra], key=lambda p: p.utc)
        keys = [p.utc for p in pts]
        i = bisect.bisect_left(keys, utc_target)
        return (pts[i - 1] if i > 0 else None), (pts[i] if i < len(pts) else None)
