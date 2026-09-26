"""예측 r4 관측 생성(순수) — 활동 목록(get_runs 형식) → 전력 대회·품질 세트·심박-속도 H·Tanda·롱런 입력.

runs 원소: get_runs(with_laps=True) dict + "ambient_c"(외기, 없으면 None) + "effort"·"official_time_s"(race_results).
세트는 GPS·시간만으로 만든다(HR 불필요). HR 은 세트 품질 배율과 H 에만 쓴다(REVIEW-09 §3·§5).
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, median

from src.metrics import segments as seg
from src.metrics.prediction.core_r4 import MAINT_ALPHA, SIGMA_RACE, SIGMA_SET, hr_reach_mult, temp_factor, vdot, vdot_at_15c
from src.metrics.prediction.effort import auto_effort
from src.metrics.prediction.daniels import equivalent_minutes, set_vdot, threshold_speed

EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running", "trail_running")
H_DAYS = 60
H_MIN_POINTS = 25
EASY_DAYS = 90
DEFAULT_V_EASY = 1000 / 360.0      # 이력 부족 시 6:00/km


def _days(d_from: str, d_to: str) -> int:
    return (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days


def allout_races(runs: list[dict], as_of: str, hrmax: float | None, heat: float, cold: float,
                 ctl_at=None, lthr: float | None = None) -> list[dict]:
    """전력 대회(365일). 사용자 확인 effort 가 최우선(allout 만 포함). 미확인이면 거리·지속시간별 자동 추정
    (`effort.classify`: 평균 HR/LTHR 대 기대값 + 최대 HR 도달률)이 allout 인 것만. uncertain 은 paced_races 로 간다.
    ctl_at(날짜)→CTL 이 주어지면 유지 조건부 앵커: VDOT × (1 − MAINT_ALPHA·max(0, 1 − CTL(기준일 전날)/CTL(대회일)))."""
    out = []
    for r in runs:
        n = r.get("nominal_m")
        if not r["is_race"] or not n or r["date"] >= as_of or _days(r["date"], as_of) > 365:
            continue
        eff = r.get("effort")
        if eff is not None and eff != "allout":
            continue
        t = r.get("official_time_s") or r["perf_time_s"]
        if eff is None and auto_effort(r, runs, hrmax) != "allout":
            continue
        v = vdot_at_15c(n, t, r.get("ambient_c"), heat, cold)
        loss = 0.0
        if ctl_at:
            c0, c1 = ctl_at(r["date"]), ctl_at(_prev_day(as_of))
            if c0 and c1:
                loss = MAINT_ALPHA * max(0.0, 1.0 - c1 / c0)
        out.append({"activity_id": r["id"], "date": r["date"], "nominal_m": n, "time_s": t,
                    "day": -_days(r["date"], as_of), "vdot15": v * (1.0 - loss), "maint_loss": round(loss, 4),
                    "auto": eff is None})
    return out


def _prev_day(d: str) -> str:
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()


def easy_speeds(runs: list[dict]) -> dict[int, float]:
    """활동별 이지 기준 속도 = 직전 90일 비대회 러닝(≥4km)의 '랩 속도 중앙값'들의 중앙값(5개 미만이면 6:00/km)."""
    meds = [(r["date"], median(b["speed_ms"] for b in r["laps"])) for r in runs
            if not r["is_race"] and r["distance_m"] >= 4000 and r.get("laps")]
    out = {}
    for r in runs:
        m = [v for d, v in meds if 0 < _days(d, r["date"]) <= EASY_DAYS]
        out[r["id"]] = median(m) if len(m) >= 5 else DEFAULT_V_EASY
    return out


def set_obs(r: dict, v_easy: float, hrmax: float | None) -> dict | None:
    """활동 1개 → 품질 세트 관측 1개(없으면 None). 기온 정규화하지 않는다(REVIEW-09 §3-3)."""
    laps = r.get("laps") or []
    if r["is_race"] or r["activity_type"] in EXCLUDE_TYPES or len(laps) < 2:
        return None
    bouts = seg.build_bouts(laps, seg.label_blocks(laps, v_easy))
    ws = seg.work_set(bouts)
    if not ws or ws["zone"] is None or ws["speed_ms"] < seg.QUALITY_CONTRAST * v_easy:
        return None
    peaks = [b["max_hr"] for b in bouts[len(bouts) // 2:] if b.get("max_hr")]
    reach = max(peaks) / hrmax if (peaks and hrmax) else None
    teq = equivalent_minutes(ws["n"], ws["rho"])
    native = {"R": 1609.344, "M": 42195.0}.get(ws["zone"], ws["speed_ms"] * teq * 60.0)
    return {"date": r["date"], "kind": ws["zone"], "y": set_vdot(ws["zone"], ws["speed_ms"], ws["n"], ws["rho"]),
            "var": SIGMA_SET ** 2 * hr_reach_mult(reach), "native_m": native, "activity_id": r["id"],
            "n": ws["n"], "rho": ws["rho"], "rep_s": ws["rep_s"], "hr_reach": reach and round(reach, 3)}


def paced_races(runs: list[dict], as_of: str, heat: float, cold: float, hrmax: float | None = None,
                lthr: float | None = None) -> list[dict]:
    """최대 이하 대회 → 하한 증거 관측(kind 'paced', 세트와 같은 분산). 사용자가 effort='paced'로 확인한 대회와,
    미확인이면서 자동 추정이 uncertain 인 대회(uncertain=True — 이유 문구로 확인 요청). 자동 submax(펀런 등)는 버린다.
    15℃ 환산은 대회와 같게 한다. 앵커(전력 대회)에서는 빠진다."""
    out = []
    for r in runs:
        n = r.get("nominal_m")
        if not (r["is_race"] and n and r["date"] < as_of and _days(r["date"], as_of) <= 365):
            continue
        t = r.get("official_time_s") or r["perf_time_s"]
        eff = r.get("effort")
        unsure = eff is None and auto_effort(r, runs, hrmax) == "uncertain"
        if eff == "paced" or unsure:
            out.append({"date": r["date"], "kind": "paced", "y": vdot_at_15c(n, t, r.get("ambient_c"), heat, cold),
                        "var": SIGMA_SET ** 2, "native_m": n, "activity_id": r["id"], "uncertain": unsure})
    return out


def observations(runs: list[dict], as_of: str, races: list[dict], hrmax: float | None,
                 paced: list[dict] | None = None) -> list[dict]:
    """전력 대회 + 최대 이하 대회(하한) + 세트 관측(날짜순, 365일). 대회 관측의 고유 거리 = 대회 거리."""
    ve = easy_speeds(runs)
    obs = [{"date": x["date"], "kind": "race", "y": x["vdot15"], "var": SIGMA_RACE ** 2, "native_m": x["nominal_m"],
            "activity_id": x["activity_id"]} for x in races] + list(paced or [])
    for r in runs:
        if r["date"] < as_of and _days(r["date"], as_of) <= 365:
            o = set_obs(r, ve[r["id"]], hrmax)
            if o:
                obs.append(o)
    return sorted(obs, key=lambda o: (o["date"], o["kind"] != "race"))


def steady_points(r: dict) -> list[tuple[float, float, float]]:
    """정상 주행 1km 랩(3번째 랩부터, HR 110~190, 3:50~7:30/km) → (hr, speed, ambient)."""
    if r["is_race"] or r["activity_type"] in EXCLUDE_TYPES or r.get("ambient_c") is None:
        return []
    out = []
    for b in (r.get("laps") or [])[2:]:
        if 900 <= b["dist_m"] <= 1100 and b["hr"] and 110 <= b["hr"] <= 190 and 1000 / 450 <= b["speed_ms"] <= 1000 / 230:
            out.append((b["hr"], b["speed_ms"], r["ambient_c"]))
    return out


def hr_signal(runs: list[dict], as_of: str, lthr: float | None, heat: float, cold: float) -> float | None:
    """최근 60일 HR–속도(15℃ 정규화) 직선의 LTHR 속도 → T 구간(60분 레이스) VDOT."""
    if not lthr:
        return None
    pts = [p for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= H_DAYS for p in steady_points(r)]
    if len(pts) < H_MIN_POINTS:
        return None
    x = [h for h, _, _ in pts]
    y = [v / temp_factor(t, heat, cold) for _, v, t in pts]
    mx, my = mean(x), mean(y)
    sxx = sum((q - mx) ** 2 for q in x)
    if not sxx:
        return None
    b = sum((q - mx) * (w - my) for q, w in zip(x, y)) / sxx
    v = my + b * (lthr - mx)
    return vdot(v * 3600, 3600) if v > 0 else None


def h_native_m(h: float) -> float:
    return threshold_speed(h) * 3600.0


def tanda_inputs(runs: list[dict], as_of: str) -> tuple[float, float, int]:
    """(최근 8주 주평균 km, 평균 이동 페이스 s/km, 12주 내 28km+ 롱런 수)."""
    r8 = [r for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= 56]
    km = sum(r["distance_m"] for r in r8) / 1000.0
    mv = sum(r["moving_s"] for r in r8)
    long28 = sum(1 for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= 84 and r["distance_m"] >= 28000)
    return km / 8.0, (mv / km if km else 0.0), long28


def longest_run_m(runs: list[dict], as_of: str, days: int = 84) -> float | None:
    """최근 12주 최장 러닝 거리(m) — 롱런 외삽 분산 입력(REVIEW-09 §7)."""
    ds = [r["distance_m"] for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= days
          and r["activity_type"] not in EXCLUDE_TYPES]
    return max(ds) if ds else None
