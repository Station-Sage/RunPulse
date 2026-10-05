"""준비 볼륨·경고(DESIGN-U16-LONGRUN §5.2-5)와 콜드 피크 목표(§5.2 L5 후속)."""
from datetime import date

from src.training import plan_readiness as P
from src.training import planner_schedule as S
from src.training.goals import add_goal, set_reported_load
from src.training.periodization import WeekTarget
from tests.helpers_pred import mem_conn

RACE = "2030-11-24"
TODAY = date(2030, 1, 1)


def _sched(kms: list[float]) -> list[WeekTarget]:
    n = len(kms)
    return [WeekTarget(i, n - 1 - i, "taper" if i == n - 1 else "build", km, 0.0) for i, km in enumerate(kms)]


def test_ready_and_cold_peak_km_by_distance():
    assert [P.ready_week_km(d) for d in ("full", "half", "10k", "5k")] == [40.0, 26.7, 23.3, 16.7]
    assert [P.cold_peak_km(d) for d in ("full", "half", "10k", "5k")] == [48.0, 32.0, 28.0, 20.0]
    assert P.ready_week_km("custom") == P.ready_week_km("10k")


def test_readiness_warning_ramp_message():
    msg = P.readiness_warning("full", _sched([12.0, 13.2, 14.5, 20.0]))
    assert msg.startswith("현재 주 12km로는 4주 안에 풀마라톤 준비 볼륨(주 40km)에 닿기 어렵습니다")
    assert "최대 주 14.5km" in msg            # 감량 주(20.0)는 피크 판정에서 뺀다


def test_readiness_warning_none_when_reached_or_empty():
    assert P.readiness_warning("full", _sched([36.0, 39.6, 40.0, 20.0])) is None
    assert P.readiness_warning("half", []) is None


def test_readiness_warning_days_cap_message():
    msg = P.readiness_warning("full", _sched([20.0, 22.0, 24.0, 10.0]), max_week_km=30.0)
    assert "러닝 일수" in msg and "최대 30km" in msg


def _goal(c, rv, dist=42.195, label="full", weeks=12):
    gid = add_goal(c, "g", dist, RACE, None, rules_version=rv)
    c.execute("UPDATE goals SET plan_weeks=?, distance_label=? WHERE id=?", (weeks, label, gid))
    return gid, {"id": gid, "race_date": RACE, "plan_weeks": weeks, "distance_km": dist}


def test_cold_v2_peak_aims_at_ready_volume_with_ramp_kept():
    c = mem_conn()
    _, g = _goal(c, 2, weeks=24)
    sched = S.schedule_for_goal(c, g, "full", None, TODAY)
    loads = [w.weekly_km for w in sched if w.phase not in ("taper", "recovery_week")]
    assert loads[0] == 20.0 and max(loads) > 20.0 * 1.3          # 시작 × 1.3 에 묶이지 않는다
    assert all(b <= a * 1.10 + 1e-6 for a, b in zip(loads, loads[1:]))   # 램프 10% 유지


def test_plan_warnings_cold_full_short_plan():
    c = mem_conn()
    gid, _ = _goal(c, 2, weeks=8)
    warns = P.plan_warnings(c, gid, TODAY)
    assert len(warns) == 1 and "풀마라톤 준비 볼륨" in warns[0]
    assert P.plan_warnings(c, 999, TODAY) == []


def test_plan_warnings_uses_reported_load():
    c = mem_conn()
    gid, g = _goal(c, 2, dist=10.0, label="10k", weeks=20)
    set_reported_load(c, gid, 30.0, 12.0)
    assert S.plan_start_source(c, g, "10k", TODAY) == "user"
    assert P.plan_warnings(c, gid, TODAY) == []                     # 주 30km 시작이면 10k 준비 볼륨 이상
