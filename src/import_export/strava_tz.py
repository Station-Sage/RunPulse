"""Strava CSV/ZIP 시작 시각의 시간대 해석 체인 (TZ T2, ADR-052).

CSV 는 UTC 만 주므로 현지 벽시계를 다음 순서로 구한다:
api_payload → fit_local → peer_direct → peer_derived → neighbor → fallback(KST).
가져오기 경로는 네트워크 호출 0 (TZ-7) — Strava API 조회는 백필(`tz_backfill`)에서만 한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta

from src.utils.tz_peers import PeerMatch, PeerTime, PeerTzIndex

logger = logging.getLogger(__name__)

KST_OFFSET_SEC = 9 * 3600

TZ_SOURCE_RANK: dict[str, int] = {
    "api_payload": 5, "api_fetch": 5, "fit_local": 5,
    "peer_direct": 4, "peer_derived": 3, "neighbor": 2, "fallback": 1,
}
CONFIRMED = ("api_payload", "api_fetch", "fit_local", "peer_direct")
_PROTECTED_RANK = 99  # tz_source 없는 기존 행(수동 보정 포함)은 덮어쓰지 않는다


def rank_of(tz_source: str | None) -> int:
    if not tz_source:
        return _PROTECTED_RANK
    return TZ_SOURCE_RANK.get(tz_source.split(":")[0], _PROTECTED_RANK)


def may_overwrite(new_tz_source: str, old_tz_source: str | None) -> bool:
    """새 해석이 기존 값을 덮어써도 되는가 (새 순위 ≥ 기존 순위)."""
    return rank_of(new_tz_source) >= rank_of(old_tz_source)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def load_api_payload(conn: sqlite3.Connection, source_id: str) -> dict | None:
    for et in ("activity_detail", "activity_summary"):
        row = conn.execute(
            "SELECT payload FROM source_payloads WHERE source='strava' AND entity_type=? AND entity_id=?",
            (et, str(source_id)),
        ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (ValueError, TypeError):
                continue
    return None


def _from_api(api: dict | None, utc: datetime) -> datetime | None:
    if not api:
        return None
    loc = api.get("start_date_local")
    if isinstance(loc, str) and loc:
        try:
            return datetime.fromisoformat(loc.replace("Z", "")[:19])
        except ValueError:
            pass
    off = api.get("utc_offset")
    if off is not None:
        try:
            return utc + timedelta(seconds=float(off))
        except (TypeError, ValueError):
            pass
    return None


def _same_local_day(utc: datetime, pt: PeerTime, offset_sec: int) -> bool:
    return (utc + timedelta(seconds=offset_sec)).date() == pt.local.date()


def _neighbor(peers: PeerTzIndex, utc: datetime) -> tuple[int, dict] | None:
    """5a: 같은 현지 날짜의 확정 이웃에서 오프셋 차용. 동률이면 직전."""
    prev, nxt = peers.nearest_confirmed(utc)
    cands = []
    for tag, pt in (("prev", prev), ("next", nxt)):
        if pt is None or pt.utc is None or pt.local is None:
            continue
        off = int(round((pt.local - pt.utc).total_seconds()))
        if _same_local_day(utc, pt, off):
            cands.append((tag, pt, off, abs((pt.utc - utc).total_seconds())))
    if not cands:
        return None
    if len({c[2] for c in cands}) == 1:
        chosen = cands[0]
    else:
        chosen = min(cands, key=lambda c: (c[3], 0 if c[0] == "prev" else 1))
    info = {"mode": "neighbor", **{c[0]: {"source": c[1].source, "source_id": c[1].source_id,
                                         "offset_sec": c[2]} for c in cands}}
    return chosen[2], info


def resolve_strava_start(
    conn: sqlite3.Connection,
    source_id: str,
    utc_naive: datetime,
    distance_m: float | None,
    *,
    api: dict | None = None,
    fit_local: datetime | None = None,
    peers: PeerTzIndex | None = None,
) -> tuple[str, str, dict | None]:
    """(현지 벽시계 'YYYY-MM-DDTHH:MM:SS', tz_source, tz_peer 정보|None)."""
    if api is None:
        api = load_api_payload(conn, source_id)
    local = _from_api(api, utc_naive)
    if local is not None:
        return _fmt(local), "api_payload", None
    if fit_local is not None:
        return _fmt(fit_local), "fit_local", None
    if peers is not None:
        m: PeerMatch | None = peers.lookup(utc_naive, distance_m)
        if m is not None:
            info = {"mode": "direct" if m.grade == "direct" else "derived", "source": m.source,
                    "source_id": m.source_id, "offset_sec": m.offset_sec, "delta_sec": m.delta_sec}
            if m.conflicts:
                info["conflicts"] = m.conflicts
            return (_fmt(utc_naive + timedelta(seconds=m.offset_sec)),
                    f"peer_{m.grade}:{m.source}", info)
        nb = _neighbor(peers, utc_naive)
        if nb is not None:
            off, info = nb
            src = (info.get("prev") or info.get("next"))["source"]
            return _fmt(utc_naive + timedelta(seconds=off)), f"neighbor:{src}", info
    return _fmt(utc_naive + timedelta(seconds=KST_OFFSET_SEC)), "fallback", None


class StravaTzLookup:
    """Strava API 연결 상태 + 백필용 단건 조회. 가져오기 경로에서는 상태만 쓴다."""

    def __init__(self, config: dict | None):
        self.config = config
        self.available = False
        self.status = "config 없음"
        self._token: str | None = None
        if not config:
            return
        try:
            from src.sync.strava_auth import check_strava_connection

            chk = check_strava_connection(config)
            if not chk.get("ok"):
                self.status = str(chk.get("status") or "연결 안 됨")
                return
            self.available, self.status = True, "연결됨"
        except Exception as exc:  # 연결 확인 실패는 가져오기를 막지 않는다
            logger.warning("[strava_tz] 연결 확인 실패: %s", exc)
            self.status = "확인 실패"

    def fetch(self, source_id: str) -> dict | None:
        """Strava 활동 1건 조회 (백필 전용). 실패 시 None."""
        if not self.available:
            return None
        import requests

        from src.sync.strava_auth import refresh_token

        from src.sync.rate_limiter import RateLimiter

        rl = RateLimiter("strava")
        try:
            if self._token is None:
                self._token = refresh_token(self.config)
            rl.pre_request()
            r = requests.get(f"https://www.strava.com/api/v3/activities/{source_id}",
                             headers={"Authorization": f"Bearer {self._token}"}, timeout=20)
            if r.status_code == 429:
                rl.handle_rate_limit()
                return None
            rl.post_request(r.status_code == 200)
            return r.json() if r.status_code == 200 else None
        except Exception as exc:
            logger.warning("[strava_tz] 조회 실패 %s: %s", source_id, exc)
            return None
