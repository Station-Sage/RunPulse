"""U16-LR L1: 롱런 하한·상한 순수 규칙 — 설계서 §8.1 경계값 표(#1~#17)."""
import pytest

from src.training import long_run_rules as LR


def ctx(d="full", phase="peak", w=70.0, n=5, lp=360.0, sched=0.0, long6=0.0, long12=0.0, w2r=8, **kw):
    return LR.LongCtx(d, phase, w2r, w, n, lp, sched, long6, long12, **kw)


@pytest.mark.parametrize("c, want", [
    (ctx(sched=30, long6=28, w=70, n=5), 24.0),                       # 1 표값
    (ctx(sched=14, long6=12, w=50, n=4), 14.0),                       # 2 이력 이상 강제 금지
    (ctx(phase="build", sched=6, long6=0, w=40, n=4), 12.0),          # 3 절대 최소
    (ctx(sched=30, long6=30, w=36, n=3), 21.6),                       # 4 ENV 0.6×36
    (ctx(phase="build", w2r=2, sched=30, long6=30, w=70), 20.0),      # 5 D−14
    (ctx(d="half", phase="base", sched=6.6, long6=16.2, w=13.2, n=2), 10.0),   # 6 ENV → 절대 최소
    (ctx(lp=480, sched=30, long6=30, w=70), 22.5),                    # 7 180분 시간 상한
])
def test_floor_boundaries(c, want):
    assert LR.long_floor_km(c) == pytest.approx(want, abs=1e-9)


def test_floor_uses_long12_basis():
    assert LR.basis_km(ctx(long6=10, long12=20)) == pytest.approx(17.0)
    assert LR.long_floor_km(ctx(phase="build", long6=10, long12=20, w=60)) == 17.0


def test_half_base_low_volume_week_has_no_long():   # 6: 10 + 6 > 13.2 → 롱런 없는 주
    b = LR.plan_long_budget(ctx(d="half", phase="base", sched=6.6, long6=16.2, w=13.2, n=3))
    assert not b.has_long and b.run_days == 2 and b.floor_km == 0.0


@pytest.mark.parametrize("c, want", [
    (ctx(w=60, n=4, lp=352), 30.0),                                   # 8
    (ctx(w=73.5, n=6, lp=352), 30.68),                                # 9 180분
    (ctx(phase="base", w=73.5, n=6, lp=352), 25.57),                  # 10 150분
    (ctx(w=100, n=6, long12=31, lp=300), 35.0),                       # 11 절대 35
    (ctx(w=100, n=6, long12=29, lp=300), 32.0),                       # 12 절대 32
    (ctx(d="half", phase="build", w=26.6, n=3, sched=14, long6=14), 14.0),     # 13 하한 > 비중 13.3
    (ctx(d="half", phase="build", w=50, n=5), 17.5),                  # 14 r 0.35
    (ctx(d="half", phase="build", w=50, n=5, long12=23), 22.5),       # 15 D-U16-4
])
def test_cap_boundaries(c, want):
    assert LR.long_cap_km(c) == pytest.approx(want, abs=0.01)


def test_share_ratio_by_days():                                       # 16
    assert [LR.share_ratio(ctx(d="half", phase="build", w=40, n=n)) for n in (2, 3, 4, 5)] == [0.60, 0.50, 0.45, 0.35]


def test_min_viable_week_km():                                        # 17
    assert (LR.min_viable_week_km("half", 2), LR.min_viable_week_km("full", 2),
            LR.min_viable_week_km("full", 3)) == (16.0, 18.0, 24.0)


def test_floor_never_exceeds_cap():
    for w in (20, 36, 50, 80):
        for n in (2, 3, 4, 6):
            for ph in ("base", "build", "peak", "recovery_week"):
                c = ctx(phase=ph, w=w, n=n, sched=30, long6=30, lp=420)
                assert LR.long_floor_km(c) <= LR.long_cap_km(c) + 1e-9


def test_prog_cap_only_with_prev_long():
    assert LR.prog_cap_km(ctx()) is None
    assert LR.prog_cap_km(ctx(prev_long_km=18, long6=10)) == pytest.approx(20.0)
    assert LR.prog_cap_km(ctx(prev_long_km=25)) == pytest.approx(27.5)
    assert LR.long_cap_km(ctx(w=80, n=6, prev_long_km=18)) == pytest.approx(20.0)


def test_budget_full_build_moves_mp_into_long():                      # 19(예산 부분)
    b = LR.plan_long_budget(ctx(phase="build", w=26, n=3, sched=20, long6=18), mp_week=True)
    assert b.has_long and b.run_days == 2 and b.mp_in_long and b.mp_extra_km == 0.0
    assert b.floor_km == pytest.approx(18.2)


def test_budget_relaxes_floor_before_dropping_long():
    b = LR.plan_long_budget(ctx(d="half", phase="peak", w=17, n=4, sched=16, long6=16))
    assert b.has_long and b.run_days == 2 and b.floor_km == 11.0      # 0.7×17 = 11.9 → 17 − 6 = 11


def test_budget_floor_matches_recorded_ctx():
    c = ctx(d="half", phase="peak", w=17, n=2, sched=16, long6=16)
    assert LR.budget_floor_km(c) == 11.0
    assert LR.budget_floor_km(ctx(w=70, n=5, sched=30, long6=30)) == 24.0


def test_feasible_week_km_monotone_and_full_peak_share():
    vals = [LR.feasible_week_km("full", n, 352) for n in (3, 4, 5, 6)]
    assert vals == sorted(vals) and vals[1] == pytest.approx(60.0, abs=0.1)   # 4일: 0.5W + 30 ≥ W → 60
    assert LR.feasible_week_km("half", 4) < LR.feasible_week_km("full", 4, 352)
