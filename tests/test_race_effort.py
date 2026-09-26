"""P7-PRED-22(r4 보강): 거리·지속시간별 전력 판정 — 이 러너 대회 값으로 검증(REVIEW-09 §10)."""
from src.metrics.prediction.effort import classify, expected_ratio

# (시간 s, 평균 HR, 최대 HR, HRmax, LTHR, 기대 판정) — 사본 DB 대회(집계값)
CASES = [
    (2757, 168, 184, 185.0, 170.7, "allout"),     # 2025-11-09 10K
    (2676, 173, 194, 191.0, 178.9, "allout"),     # 2026-04-11 10K
    (2759, 179, 187, 191.0, 177.6, "allout"),     # 2026-05-03 10K
    (2653, 165, 186, 191.0, 178.9, "allout"),     # 2026-05-09 10K PB — 평균 HR 낮으나 최대 도달
    (6756, 167, 184, 185.0, 170.8, "allout"),     # 2025-09-14 하프
    (6294, 169, 188, 187.0, 170.8, "allout"),     # 2026-03-02 하프
    (6150, 176, 191, 188.0, 180.2, "allout"),     # 2026-03-22 하프
    (2818, 163, 178, 192.0, 177.6, "submax"),     # 2026-09-12 Forest run — 사용자 확인: 최대 이하
    (3726, 139, 167, 191.0, 178.9, "submax"),     # 2026-05-10 10K 펀런
    (13332, 147, 158, 185.0, 170.8, "uncertain"), # 2025-10-18 풀 — HR 비율은 풀 기대 근처, 최대 도달 낮음 → 사용자 확인
]


def test_runner_races():
    for t, avg, mx, hmax, lthr, want in CASES:
        got, ev = classify(t, avg, mx, hmax, lthr)
        assert got == want, (t, avg, got, ev)


def test_expected_ratio_monotone_and_t0():
    assert expected_ratio(15) == 1.03 and expected_ratio(300) == 0.90
    assert expected_ratio(45) > expected_ratio(105) > expected_ratio(210)
    assert classify(2700, None, None, None)[0] == "allout"


def test_point_in_time_hrmax_and_proxy():
    from src.metrics.prediction.effort import auto_effort, hrmax_at
    runs = [{"date": f"2025-10-0{i}", "max_hr": 180} for i in range(1, 4)] + [
        {"date": "2025-10-10", "max_hr": 185}, {"date": "2025-10-20", "max_hr": 184},
        {"date": "2026-08-01", "max_hr": 193}, {"date": "2026-08-10", "max_hr": 192}]
    race = {"date": "2025-11-09", "perf_time_s": 2784, "avg_hr": 168, "max_hr": 184}
    assert hrmax_at(runs, "2025-11-09") == 184.0 and hrmax_at(runs, "2026-09-26") == 192.0
    assert auto_effort(race, runs + [race]) == "allout"                   # 대회일 HRmax 185 기준
    assert classify(2784, 168, 184, 192.0, 177.6)[0] != "allout"         # 현재 HRmax 192·자체 LTHR 177.6 을 쓰면 전력이 탈락
