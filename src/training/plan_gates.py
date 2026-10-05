"""계획 백테스트 게이트(순수) — 주간 계획이 구조 불변식(G1~G8)과 실행 가능성(F1~F5)을 지키는지 판정한다.

DESIGN-U16 §2.4. 입력은 엔진 중립 구조(WeekPlan/Session)이고 DB를 읽지 않는다. 각 게이트는 GateResult(통과 여부,
위반 수, 최악 사례 문자열)를 돌려준다. 수치는 설계서로 고정이라 임의로 완화하지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

MIN_SESSION_KM, MIN_SESSION_MIN = 6.0, 35.0
LONG_TOL_KM = 0.5
RAMP_MAX = 0.10
MP_FASTEST_GAP = 12.0       # 처방 MP는 현재 MP보다 12초/km보다 빠르면 안 됨
MP_MIN_SESSION_KM = 8.0


@dataclass
class Session:
    type: str                # rest | easy | long | long_mp | marathon | tempo | interval | recovery | shakeout ...
    km: float = 0.0
    mp_km: float = 0.0       # 세션 안의 MP 구간 거리
    pace_sec: float | None = None
    minutes: float | None = None


@dataclass
class WeekPlan:
    index: int
    weeks_to_race: int       # 대회 주 = 0
    phase: str
    days: list[Session] = field(default_factory=list)
    mp_sec: float | None = None   # 그 주 처방 MP(sec/km)

    @property
    def km(self) -> float:
        return sum(s.km for s in self.days)

    @property
    def run_days(self) -> int:
        return sum(1 for s in self.days if s.type != "rest" and s.km > 0)

    @property
    def long_km(self) -> float:
        return max((s.km for s in self.days if s.type in ("long", "long_mp")), default=0.0)

    @property
    def mp_session_km(self) -> float:
        return max((s.mp_km for s in self.days), default=0.0)


@dataclass
class GateResult:
    gate: str
    violations: int = 0
    worst: str = ""

    @property
    def ok(self) -> bool:
        return self.violations == 0


def _result(gate: str, bad: list[str]) -> GateResult:
    return GateResult(gate, len(bad), bad[0] if bad else "")


def g1_rest_days(weeks: list[WeekPlan], run_days: int) -> GateResult:
    bad = [f"w{w.index}: 휴식 {7 - w.run_days}일 < {7 - run_days}" for w in weeks
           if w.weeks_to_race > 0 and 7 - w.run_days < 7 - run_days]
    return _result("G1", bad)


def g2_long_cap(weeks: list[WeekPlan], cap_km) -> GateResult:
    """cap_km(week) → 그 주 롱런 상한(km)."""
    bad = [f"w{w.index}: 롱런 {w.long_km:.1f} > {cap_km(w):.1f}+{LONG_TOL_KM}" for w in weeks
           if w.long_km > cap_km(w) + LONG_TOL_KM]
    return _result("G2", bad)


def g3_min_session(weeks: list[WeekPlan]) -> GateResult:
    bad = []
    for w in weeks:
        for d, s in enumerate(w.days):
            if s.type in ("rest", "shakeout") or s.km <= 0:
                continue
            mins = s.minutes if s.minutes is not None else (s.km * s.pace_sec / 60 if s.pace_sec else None)
            if s.km < MIN_SESSION_KM and (mins is None or mins < MIN_SESSION_MIN):
                bad.append(f"w{w.index}d{d}: {s.type} {s.km:.1f}km")
    return _result("G3", bad)


def g4_mp_sessions(weeks: list[WeekPlan], distance: str) -> GateResult:
    """풀: build 시작 주부터 테이퍼 1주차까지 매주 MP 구간 ≥ 8km 세션 1회."""
    if distance != "full":
        return GateResult("G4")
    span = [w for w in weeks if w.phase in ("build", "peak")]
    taper1 = next((w for w in weeks if w.phase == "taper"), None)
    if taper1 is not None:
        span.append(taper1)
    bad = [f"w{w.index}: MP {w.mp_session_km:.1f}km < {MP_MIN_SESSION_KM}" for w in span
           if w.mp_session_km < MP_MIN_SESSION_KM]
    return _result("G4", bad)


def g5_taper(weeks: list[WeekPlan], distance: str, peak_km: float, total_weeks: int) -> GateResult:
    if distance != "full":
        return GateResult("G5")
    taper = [w for w in weeks if w.phase == "taper"]
    want = 3 if total_weeks >= 16 and peak_km >= 80 else 2
    bad = []
    if len(taper) != want:
        bad.append(f"테이퍼 {len(taper)}주 != {want}")
    ref = max((w.km for w in weeks if w.phase != "taper"), default=0.0)
    for w, f in zip(taper, (0.70, 0.50) if want == 2 else (0.75, 0.60, 0.45)):
        if ref and abs(w.km / ref - f) > 0.02:
            bad.append(f"w{w.index}: 테이퍼 비율 {w.km / ref:.2f} != {f}")
    return _result("G5", bad)


def g6_ramp(weeks: list[WeekPlan], prev4_avg: float, comeback_ceiling: float = 0.0, comeback_ramp: float = 0.15) -> GateResult:
    """부하주 간 증가율 ≤ 10%(복귀 구간은 직전 16주 평균 comeback_ceiling까지 15%), 1주차 ≤ 1.10 × prev4_avg."""
    bad = []
    load = [w for w in weeks if w.phase not in ("recovery_week", "taper")]
    if load and prev4_avg > 0 and load[0].km > prev4_avg * 1.10 + 0.05:
        bad.append(f"w{load[0].index}: 1주차 {load[0].km:.1f} > 1.10×{prev4_avg:.1f}")
    for a, b in zip(load, load[1:]):
        if a.km <= 0:
            continue
        lim = comeback_ramp if b.km <= comeback_ceiling else RAMP_MAX
        if b.km / a.km - 1 > lim + 0.005:
            bad.append(f"w{b.index}: 증가 {b.km / a.km - 1:+.1%}")
    return _result("G6", bad)


def g7_mp_not_faster(weeks: list[WeekPlan], mp_now) -> GateResult:
    """mp_now(week) → 그 주 현재 MP(sec/km) 또는 None."""
    bad = []
    for w in weeks:
        now = mp_now(w)
        if w.mp_sec is not None and now is not None and w.mp_sec < now - MP_FASTEST_GAP - 0.01:
            bad.append(f"w{w.index}: MP {w.mp_sec:.0f} < {now:.0f}-{MP_FASTEST_GAP:.0f}")
    return _result("G7", bad)


def serialize(weeks: list[WeekPlan]) -> str:
    return json.dumps([asdict(w) for w in weeks], ensure_ascii=False, sort_keys=True)


def g8_deterministic(run) -> GateResult:
    """run() 을 두 번 호출해 직렬화 결과가 같은지."""
    a, b = serialize(run()), serialize(run())
    return _result("G8", [] if a == b else ["같은 입력에서 출력이 다름"])


def f1_start_fit(weeks: list[WeekPlan], prev4_avg: float) -> GateResult:
    if not weeks or prev4_avg <= 0:
        return GateResult("F1")
    r = weeks[0].km / prev4_avg
    return _result("F1", [] if 0.90 <= r <= 1.10 else [f"1주차/직전4주 = {r:.2f}"])


def f2_peak_long(weeks: list[WeekPlan], actual_long_12w: float) -> GateResult:
    peak = max((w.long_km for w in weeks), default=0.0)
    return _result("F2", [] if peak <= actual_long_12w + 6 else [f"피크 롱런 {peak:.1f} > {actual_long_12w:.1f}+6"])


def f3_peak_week(weeks: list[WeekPlan], actual_peak_16w: float) -> GateResult:
    peak = max((w.km for w in weeks), default=0.0)
    return _result("F3", [] if peak <= 1.25 * actual_peak_16w else [f"피크 주 {peak:.1f} > 1.25×{actual_peak_16w:.1f}"])


def f4_total_ratio(v2: list[WeekPlan], v1: list[WeekPlan]) -> GateResult:
    t1 = sum(w.km for w in v1)
    if t1 <= 0:
        return GateResult("F4")
    r = sum(w.km for w in v2) / t1
    return _result("F4", [] if 0.85 <= r <= 1.10 else [f"v2/v1 총 km = {r:.2f}"])


def f5_race_pace(race_pace_sec: float, race_week_mp: float | None) -> GateResult:
    if race_week_mp is None:
        return _result("F5", ["대회 주 처방 MP 없음"])
    ok = race_week_mp * 0.97 <= race_pace_sec <= race_week_mp * 1.05
    return _result("F5", [] if ok else [f"실제 {race_pace_sec:.0f} vs 처방 MP {race_week_mp:.0f}"])
