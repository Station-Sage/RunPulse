"""Workout Classifier v2 — 세그먼트(랩 구조) 기반 세션 유형 판정(REVIEW-07 r4, REVIEW-09 §3, P7-PRED-23).

활동 전체 평균 HR·평균 페이스를 강도 판정에 쓰지 않는다. 랩(없으면 스트림)을 워밍업·작업·휴식·쿨다운으로
분해하고 작업 구간 강도·세트 수·휴식 비율로 유형을 정한다.
text_value: easy | recovery | long_run | steady | tempo | interval | repetition | sprint | race
json_value: {"type", "source", "bouts", "sets", "n_strides", "warmup_s", "work_s", "rest_s", "cooldown_s", "v_easy"}
"""
from __future__ import annotations

from statistics import median

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics import segments as seg

RUN_TYPES = ("running", "trail_running", "treadmill", "indoor_running", "virtual_running")
DEFAULT_V_EASY = 1000 / 360.0     # 6:00/km — 이력이 없을 때


class WorkoutClassifier(MetricCalculator):
    name = "workout_type_classified"
    provider = "runpulse:rule_v1"
    version = "2.0"
    scope_type = "activity"
    category = "meta"
    display_name = "운동 유형"
    description = "랩·스트림 세그먼트(작업/휴식/세트) 기반 세션 유형."
    format_type = "json"
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in RUN_TYPES:
            return []
        date = (act.get("start_time") or "")[:10]
        v_easy = self._easy_speed(ctx, date)
        blocks, source = self._blocks(ctx, act)
        if not blocks:
            return []
        labels = seg.label_blocks(blocks, v_easy)
        bouts = seg.build_bouts(blocks, labels)
        n_strides = labels.count("stride")
        total_s = act.get("moving_time_sec") or act.get("duration_sec") or 0
        total_m = act.get("distance_m") or 0
        runs = ctx.get_runs(1, end_date=date, include_end=True) if date else []
        is_race = any(r["id"] == act.get("id") and r["is_race"] for r in runs)
        typ = seg.session_type(bouts, total_s, total_m, v_easy, is_race, n_strides)
        if typ == "long":
            typ = "long_run"
        if typ == "easy" and total_m < 7000 and self._slow(blocks, v_easy):
            typ = "recovery"
        spans = {k: round(sum(b["dur_s"] for b, lab in zip(blocks, labels) if lab == k), 1)
                 for k in ("warmup", "work", "rest", "cooldown")}
        conf = {"laps": 0.8, "streams": 0.6}.get(source, 0.4)
        payload = {"type": typ, "confidence": conf, "source": source, "bouts": bouts[:30], "sets": seg.set_summary(bouts),
                   "n_strides": n_strides, **{f"{k}_s": v for k, v in spans.items()},
                   "v_easy": round(v_easy, 3)}
        return [self._result(json_val=payload, text=typ, confidence=conf)]

    @staticmethod
    def _slow(blocks: list[dict], v_easy: float) -> bool:
        d = sum(b["dist_m"] for b in blocks)
        t = sum(b["dur_s"] for b in blocks)
        return bool(t) and d / t < 0.93 * v_easy

    @staticmethod
    def _easy_speed(ctx: CalcContext, date: str) -> float:
        """직전 90일 비대회 러닝의 '랩 속도 중앙값'들의 중앙값."""
        if not date:
            return DEFAULT_V_EASY
        meds = []
        for r in ctx.get_runs(90, end_date=date, with_laps=True, include_end=False):
            if r["is_race"] or r["distance_m"] < 4000 or not r.get("laps"):
                continue
            meds.append(median(b["speed_ms"] for b in r["laps"]))
        return median(meds) if len(meds) >= 5 else DEFAULT_V_EASY

    @staticmethod
    def _summary_block(act: dict) -> list[dict]:
        """랩·스트림이 없는 활동: 활동 전체를 블록 1개로(정확도 낮음, confidence 0.4)."""
        d = act.get("distance_m") or 0
        t = act.get("moving_time_sec") or act.get("duration_sec") or 0
        if d <= 0 or t <= 0:
            return []
        return [{"dist_m": d, "dur_s": t, "speed_ms": d / t, "hr": act.get("avg_hr"),
                 "max_hr": act.get("max_hr"), "itype": None}]

    @staticmethod
    def _blocks(ctx: CalcContext, act: dict) -> tuple[list[dict], str]:
        laps = ctx.get_laps()
        blocks = []
        for lap in laps:
            d = lap.get("distance_m") or 0
            t = lap.get("duration_sec") or 0
            if d > 0 and t > 0:
                blocks.append({"dist_m": d, "dur_s": t, "speed_ms": lap.get("gap_speed_ms") or d / t,
                               "hr": lap.get("avg_hr"), "max_hr": lap.get("max_hr"), "itype": lap.get("lap_trigger")})
        if len(blocks) >= 2:
            return blocks, "laps"
        streams = ctx.get_streams()
        if len(streams) < 60:
            return WorkoutClassifier._summary_block(act), "summary"
        dur = act.get("elapsed_time_sec") or act.get("duration_sec") or act.get("moving_time_sec") or 0
        t = seg.repair_time_axis([s.get("elapsed_sec") or 0 for s in streams], dur,
                                (ctx.get_stream_meta() or {}).get("time_basis"))
        dist = [s.get("distance_m") for s in streams]
        if any(x is None for x in dist):
            dist = seg.cumulative_distance(t, [s.get("gap_speed_ms") or s.get("speed_ms") for s in streams])
        return seg.stream_to_blocks(t, dist, [s.get("heart_rate") for s in streams]), "streams"
