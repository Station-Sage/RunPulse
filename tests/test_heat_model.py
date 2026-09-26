"""P7-PRED-33: 기온 계수 적합 + 수축."""
from src.metrics.heat_model import fit_heat, ols


def test_ols_exact():
    X = [[1, x] for x in range(5)]
    assert [round(v, 6) for v in ols(X, [2 + 3 * x for x in range(5)])] == [2.0, 3.0]


def test_few_points_returns_default():
    f = fit_heat([(150, 3.0, 20)] * 10)
    assert (f["heat"], f["cold"], f["weight"]) == (-0.62, -0.84, 0.0)


def test_shrinkage_toward_truth():
    pts = []
    for i in range(400):
        hr = 140 + (i % 30)
        t = -5 + (i % 37)
        v = (1.0 + 0.0125 * hr) * (1 - 0.01 * max(0, t - 15) - 0.005 * max(0, 5 - t))
        pts.append((hr, v, t))
    f = fit_heat(pts)
    assert f["weight"] == 0.5
    assert -1.0 < f["raw_heat"] < -0.9 and -0.55 < f["raw_cold"] < -0.45
    assert round(f["heat"], 2) == round((-0.62 + f["raw_heat"]) / 2, 2)
