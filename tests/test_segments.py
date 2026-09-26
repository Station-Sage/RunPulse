"""P7-PRED-21: 세그먼트 분해 r4 — 구조 기반 세트 구간·세션 유형(기기 불필요)."""
from src.metrics.segments import (label_blocks, build_bouts, session_type, set_summary, stream_to_blocks,
                                  repair_time_axis, cumulative_distance, work_set)

V_EASY = 1000 / 350          # 5:50/km


def B(d, s, hr=None, it=None, mx=None):
    return {"dur_s": s, "dist_m": d, "speed_ms": d / s, "hr": hr, "max_hr": mx, "itype": it}


def test_interval_6x1000_jog_rest():
    blocks = [B(2000, 720, 130, "WARMUP")]
    for _ in range(6):
        blocks += [B(1000, 250, 165, "ACTIVE", 172), B(300, 120, 140, "RECOVERY")]
    blocks += [B(1500, 540, 135, "COOLDOWN")]
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert len(bouts) == 6 and bouts[0]["hr_drop"] == 32.0 and bouts[0]["rest_speed_ms"] == 2.5
    ws = work_set(bouts)
    assert ws["rho"] == 0.48 and ws["zone"] == "I"
    assert session_type(bouts, 4500, 11300, V_EASY) == "interval"
    s = set_summary(bouts)
    assert s["n_sets"] == 6 and s["zone"] == "I" and s["rest_work_ratio"] == 0.48


def test_float_rest_is_not_rest():
    blocks = []
    for _ in range(3):
        blocks += [B(2000, 520, 170, "ACTIVE"), B(1000, 340, 150, "ACTIVE")]   # 1km 플로트 5:40 (작업의 76%)
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    ws = work_set(bouts)
    assert ws["rho"] == 0.0 and ws["zone"] == "T"


def test_stride_tail_merged_into_work():
    blocks = [B(1000, 360, 130, "WARMUP"), B(1000, 285, 160, "ACTIVE"), B(50, 14, 160, "ACTIVE"), B(200, 90, 140, "RECOVERY"),
              B(1000, 285, 165, "ACTIVE"), B(50, 14, 165, "ACTIVE"), B(500, 200, 140, "COOLDOWN")]
    lab = label_blocks(blocks, V_EASY)
    assert lab.count("stride") == 0
    bouts = build_bouts(blocks, lab)
    assert len(bouts) == 2 and bouts[0]["dur_s"] == 299.0


def test_continuous_tempo_auto_laps_no_itype():
    blocks = [B(1000, 360, 135), B(1000, 355, 138)] + [B(1000, 272, 170) for _ in range(4)] + [B(1000, 370, 150)]
    lab = label_blocks(blocks, V_EASY)
    assert lab[:2] == ["warmup", "warmup"] and lab[-1] == "cooldown"
    bouts = build_bouts(blocks, lab)
    assert len(bouts) == 1 and bouts[0]["dur_s"] == 1088.0
    assert session_type(bouts, 2445, 7000, V_EASY) == "tempo"


def test_slow_block_is_not_quality():
    blocks = [B(1000, 345, 140)] * 2 + [B(1000, 310, 150)] * 3 + [B(1000, 345, 140)]   # 5:10 = 이지의 1.13배
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert session_type(bouts, 1990, 6000, V_EASY) == "steady"


def test_repetition_and_sprint():
    blocks = [B(2000, 700, 130, "WARMUP")]
    for _ in range(8):
        blocks += [B(400, 88, 170, "ACTIVE"), B(200, 180, 120, "REST")]
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert work_set(bouts)["zone"] == "R" and session_type(bouts, 2800, 6800, V_EASY) == "repetition"
    blocks = [B(2000, 700, 130, "WARMUP")]
    for _ in range(6):
        blocks += [B(80, 15, 150, "INTERVAL"), B(300, 120, 125, "REST")]
    lab = label_blocks(blocks, V_EASY)
    assert lab.count("stride") == 6
    assert session_type(build_bouts(blocks, lab), 1500, 4280, V_EASY, n_strides=6) == "sprint"


def test_easy_long_race():
    blocks = [B(1000, 345, 140) for _ in range(10)]
    assert session_type(build_bouts(blocks, label_blocks(blocks, V_EASY)), 3450, 10000, V_EASY) == "easy"
    blocks = [B(1000, 350, 142) for _ in range(20)]
    assert session_type(build_bouts(blocks, label_blocks(blocks, V_EASY)), 7000, 20000, V_EASY) == "long"
    assert session_type([], 2700, 10000, V_EASY, is_race=True) == "race"


def test_set_drop():
    bouts = [{"dur_s": 240, "dist_m": 1000, "speed_ms": 1000 / 240, "hr": 165, "max_hr": 170, "rest_s": 90, "rest_hr": 140, "hr_drop": 30}] * 2 + \
            [{"dur_s": 260, "dist_m": 1000, "speed_ms": 1000 / 260, "hr": 170, "max_hr": 176, "rest_s": 90, "rest_hr": 150, "hr_drop": 26}] * 2
    assert set_summary(bouts)["speed_drop_pct"] == 7.7


def test_stream_blocks_detect_alternation():
    t = list(range(0, 1201)); d = [0.0]; hr = [140] * 1201
    for i in range(1, 1201):
        v = 4.0 if (i // 120) % 2 == 1 else 2.6
        d.append(d[-1] + v)
    blocks = stream_to_blocks(t, d, hr)
    assert len(build_bouts(blocks, label_blocks(blocks, 2.8))) == 5


def test_time_axis_repair():
    assert repair_time_axis([0, 1, 2, 3], 30) == [0.0, 10.0, 20.0, 30.0]
    assert repair_time_axis([0, 10, 20, 29], 30) == [0, 10, 20, 29]
    assert cumulative_distance([0, 10, 20], [None, 3.0, 3.0]) == [0.0, 30.0, 60.0]
