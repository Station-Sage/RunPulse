#!/usr/bin/env python3
"""
감사 보고서 v3에 FIT 파일 분석 결과 추가 (Addendum)
+ export_column_inventory_v3.json 업데이트
"""
import json, os
from datetime import datetime

BASE = os.path.expanduser("~/projects/RunPulse")
AUDIT_DIR = os.path.join(BASE, "audit", "reports")
REPORT_PATH = os.path.join(AUDIT_DIR, "step2_export_audit_report_v3.txt")
JSON_PATH = os.path.join(AUDIT_DIR, "export_column_inventory_v3.json")

# ── FIT 분석 결과 (위 실행 결과 기반) ──
FIT_STATS = {
    "total_files": 355,
    "size_min": 230,
    "size_max": 453522,
    "size_avg": 55050,
}

FIT_RECORD_FIELDS = {
    "timestamp":              {"files": 355, "pct": 100, "category": "시간"},
    "heart_rate":             {"files": 340, "pct": 96,  "category": "심박"},
    "distance":               {"files": 331, "pct": 93,  "category": "거리"},
    "cadence":                {"files": 251, "pct": 71,  "category": "케이던스"},
    "power":                  {"files": 227, "pct": 64,  "category": "파워"},
    "position_lat":           {"files": 208, "pct": 59,  "category": "GPS"},
    "position_long":          {"files": 208, "pct": 59,  "category": "GPS"},
    "enhanced_speed":         {"files": 184, "pct": 52,  "category": "속도"},
    "enhanced_altitude":      {"files": 166, "pct": 47,  "category": "고도"},
    "vertical_ratio":         {"files": 178, "pct": 50,  "category": "러닝다이내믹스"},
    "vertical_oscillation":   {"files": 178, "pct": 50,  "category": "러닝다이내믹스"},
    "stance_time":            {"files": 178, "pct": 50,  "category": "러닝다이내믹스"},
    "stance_time_balance":    {"files": 118, "pct": 33,  "category": "러닝다이내믹스"},
    "stance_time_percent":    {"files": 118, "pct": 33,  "category": "러닝다이내믹스"},
    "step_length":            {"files": 178, "pct": 50,  "category": "러닝다이내믹스"},
    "fractional_cadence":     {"files": 178, "pct": 50,  "category": "케이던스"},
    "accumulated_power":      {"files": 178, "pct": 50,  "category": "파워"},
    "temperature":            {"files": 164, "pct": 46,  "category": "온도"},
    "activity_type":          {"files": 178, "pct": 50,  "category": "메타"},
    "speed":                  {"files": 6,   "pct": 2,   "category": "속도"},
    "altitude":               {"files": 1,   "pct": 0,   "category": "고도"},
    "calories":               {"files": 18,  "pct": 5,   "category": "칼로리"},
}

FIT_SESSION_KNOWN = [
    "avg_cadence", "avg_cadence_position", "avg_combined_pedal_smoothness",
    "avg_fractional_cadence", "avg_heart_rate", "avg_left_pco",
    "avg_left_pedal_smoothness", "avg_left_power_phase", "avg_left_power_phase_peak",
    "avg_left_torque_effectiveness", "avg_power", "avg_power_position",
    "avg_right_pco", "avg_right_pedal_smoothness", "avg_right_power_phase",
    "avg_right_power_phase_peak", "avg_right_torque_effectiveness",
    "avg_running_cadence", "avg_speed", "avg_stance_time",
    "avg_stance_time_balance", "avg_stance_time_percent", "avg_step_length",
    "avg_stroke_count", "avg_stroke_distance", "avg_temperature",
    "avg_vertical_oscillation", "avg_vertical_ratio",
    "enhanced_avg_speed", "enhanced_max_speed",
    "event", "event_group", "event_type", "first_lap_index",
    "intensity_factor", "left_right_balance",
    "max_cadence", "max_cadence_position", "max_fractional_cadence",
    "max_heart_rate", "max_power", "max_power_position",
    "max_running_cadence", "max_speed", "max_temperature",
    "message_index", "min_heart_rate",
    "nec_lat", "nec_long", "normalized_power",
    "num_active_lengths", "num_laps", "pool_length", "pool_length_unit",
    "sport", "stand_count",
    "start_position_lat", "start_position_long", "start_time",
    "sub_sport", "swc_lat", "swc_long", "swim_stroke",
    "threshold_power", "time_standing", "timestamp",
    "total_anaerobic_training_effect", "total_ascent", "total_calories",
    "total_cycles", "total_descent", "total_distance",
    "total_elapsed_time", "total_fractional_cycles",
    "total_moving_time", "total_strides", "total_timer_time",
    "total_training_effect", "total_work",
    "training_stress_score", "trigger",
]

FIT_LAP_KNOWN = [
    "avg_cadence_position", "avg_combined_pedal_smoothness",
    "avg_fractional_cadence", "avg_heart_rate", "avg_left_pco",
    "avg_left_pedal_smoothness", "avg_left_power_phase", "avg_left_power_phase_peak",
    "avg_left_torque_effectiveness", "avg_power", "avg_power_position",
    "avg_right_pco", "avg_right_pedal_smoothness", "avg_right_power_phase",
    "avg_right_power_phase_peak", "avg_right_torque_effectiveness",
    "avg_running_cadence", "avg_stance_time", "avg_stance_time_balance",
    "avg_stance_time_percent", "avg_step_length", "avg_stroke_distance",
    "avg_temperature", "avg_vertical_oscillation", "avg_vertical_ratio",
    "end_position_lat", "end_position_long",
    "enhanced_avg_altitude", "enhanced_avg_speed",
    "enhanced_max_altitude", "enhanced_max_speed", "enhanced_min_altitude",
    "event", "event_group", "event_type", "first_length_index",
    "intensity", "lap_trigger", "left_right_balance",
    "max_cadence_position", "max_fractional_cadence", "max_heart_rate",
    "max_power", "max_power_position", "max_running_cadence", "max_temperature",
    "message_index", "normalized_power", "num_active_lengths", "num_lengths",
    "sport", "stand_count",
    "start_position_lat", "start_position_long", "start_time",
    "sub_sport", "swim_stroke", "time_standing", "timestamp",
    "total_ascent", "total_calories", "total_cycles", "total_descent",
    "total_distance", "total_elapsed_time", "total_fat_calories",
    "total_fractional_cycles", "total_moving_time", "total_strides",
    "total_timer_time", "total_work", "wkt_step_index",
]

# ── 보고서 Addendum 추가 ──
with open(REPORT_PATH, 'a', encoding='utf-8') as f:
    f.write("\n")
    f.write("=" * 70 + "\n")
    f.write("  ADDENDUM: Strava FIT.GZ 파일 전수 분석 결과\n")
    f.write(f"  추가일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")
    
    # ── A1: FIT 파일 개요 ──
    f.write("─" * 70 + "\n")
    f.write("  A1. FIT 파일 개요\n")
    f.write("─" * 70 + "\n")
    f.write(f"  총 파일 수: {FIT_STATS['total_files']}개\n")
    f.write(f"  크기 범위: {FIT_STATS['size_min']:,} ~ {FIT_STATS['size_max']:,} bytes\n")
    f.write(f"  평균 크기: {FIT_STATS['size_avg']:,} bytes ({FIT_STATS['size_avg']/1024:.1f} KB)\n")
    f.write(f"  전체 크기: ~{FIT_STATS['total_files'] * FIT_STATS['size_avg'] / 1024 / 1024:.1f} MB (압축 상태)\n\n")
    f.write("  FIT = Garmin 바이너리 포맷. TCX/GPX 대비 훨씬 풍부한 필드 포함.\n")
    f.write("  특히 러닝 다이내믹스, 파워, 온도 등 Garmin 기기 고유 데이터 보유.\n\n")
    
    # ── A2: 메시지 타입 ──
    f.write("─" * 70 + "\n")
    f.write("  A2. FIT 메시지 타입 (스키마 영향)\n")
    f.write("─" * 70 + "\n\n")
    
    msg_types_impact = [
        ("record (시계열)",   "355/355 (100%)", "→ activity_streams 테이블", "최대 29개 알려진 필드"),
        ("session (세션요약)", "355/355 (100%)", "→ activities 테이블 보강",  f"{len(FIT_SESSION_KNOWN)}개 알려진 필드 + unknown"),
        ("lap (랩요약)",      "348/355 (98%)",  "→ activity_laps 테이블",   f"{len(FIT_LAP_KNOWN)}개 알려진 필드 + unknown"),
        ("device_info",      "185/355 (52%)",  "→ 장비 메타데이터",        "29개 필드"),
        ("workout/step",     "91/355 (26%)",   "→ 운동 계획 구조",        "workout + step 데이터"),
        ("gps_metadata",     "165/355 (46%)",  "→ GPS 보정 데이터",       "altitude, speed"),
        ("hrv",              "7/355 (2%)",     "→ HRV 데이터",           "RR 인터벌"),
    ]
    
    f.write(f"  {'메시지 타입':<22} {'출현율':<18} {'스키마 매핑':<25} {'비고'}\n")
    f.write(f"  {'─'*22} {'─'*18} {'─'*25} {'─'*25}\n")
    for mt, pct, mapping, note in msg_types_impact:
        f.write(f"  {mt:<22} {pct:<18} {mapping:<25} {note}\n")
    f.write("\n")
    
    # ── A3: record 필드 상세 ──
    f.write("─" * 70 + "\n")
    f.write("  A3. FIT record 필드 (시계열 — activity_streams 확장)\n")
    f.write("─" * 70 + "\n\n")
    f.write("  기존 TCX/GPX streams: timestamp, lat, lon, altitude, HR, cadence, speed\n")
    f.write("  FIT 추가 필드:\n\n")
    
    categories = {}
    for field, info in FIT_RECORD_FIELDS.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((field, info["files"], info["pct"]))
    
    for cat, fields in categories.items():
        f.write(f"  [{cat}]\n")
        for field, files, pct in sorted(fields, key=lambda x: -x[2]):
            marker = "★" if field not in ["timestamp", "heart_rate", "distance", 
                                          "cadence", "position_lat", "position_long",
                                          "enhanced_speed", "enhanced_altitude",
                                          "speed", "altitude"] else " "
            f.write(f"    {marker} {field:<30} {files:>3}/355 ({pct:>3}%)\n")
        f.write("\n")
    
    new_stream_fields = [
        "power", "accumulated_power", "temperature",
        "vertical_oscillation", "vertical_ratio", 
        "stance_time", "stance_time_balance", "stance_time_percent",
        "step_length", "fractional_cadence", "activity_type"
    ]
    f.write(f"  → activity_streams 테이블에 추가해야 할 신규 필드: {len(new_stream_fields)}개\n")
    for nf in new_stream_fields:
        info = FIT_RECORD_FIELDS[nf]
        f.write(f"    + {nf:<30} ({info['files']}/355, {info['pct']}%)\n")
    f.write("\n")
    
    # ── A4: session 필드 → activities 테이블 보강 ──
    f.write("─" * 70 + "\n")
    f.write("  A4. FIT session 필드 → activities 테이블 보강 필요\n")
    f.write("─" * 70 + "\n\n")
    f.write(f"  session 알려진 필드: {len(FIT_SESSION_KNOWN)}개\n")
    f.write(f"  (+ unknown 필드 {132 - len(FIT_SESSION_KNOWN)}개 제외)\n\n")
    
    new_session_fields = [
        ("threshold_power",                "파워 역치 — Garmin FTP"),
        ("training_stress_score",          "TSS — Garmin 계산"),
        ("intensity_factor",               "IF — NP/FTP"),
        ("total_training_effect",          "유산소 훈련 효과 (1.0~5.0)"),
        ("total_anaerobic_training_effect", "무산소 훈련 효과"),
        ("avg_stance_time",                "평균 지면접촉시간 (ms)"),
        ("avg_stance_time_balance",        "좌우 지면접촉시간 밸런스 (%)"),
        ("avg_stance_time_percent",        "지면접촉시간 비율 (%)"),
        ("avg_vertical_oscillation",       "평균 수직진동 (cm)"),
        ("avg_vertical_ratio",             "평균 수직비율 (%)"),
        ("avg_step_length",                "평균 보폭 (m)"),
        ("avg_left_torque_effectiveness",  "왼발 토크 효율"),
        ("avg_right_torque_effectiveness", "오른발 토크 효율"),
        ("avg_left_pedal_smoothness",      "왼발 페달 매끄러움"),
        ("avg_right_pedal_smoothness",     "오른발 페달 매끄러움"),
        ("left_right_balance",             "좌우 밸런스"),
        ("normalized_power",               "NP (정규화 파워)"),
        ("total_work",                     "총 일량 (J)"),
        ("total_strides",                  "총 보폭 수"),
        ("total_moving_time",              "실제 이동 시간"),
        ("total_fat_calories",             "지방 연소 칼로리"),
        ("min_heart_rate",                 "최저 심박"),
        ("stand_count",                    "서있기 횟수"),
        ("time_standing",                  "서있기 시간"),
        ("avg_temperature",                "평균 온도"),
        ("max_temperature",                "최대 온도"),
        ("start_position_lat",             "시작 위도"),
        ("start_position_long",            "시작 경도"),
        ("nec_lat",                        "바운딩박스 북동 위도"),
        ("nec_long",                       "바운딩박스 북동 경도"),
        ("swc_lat",                        "바운딩박스 남서 위도"),
        ("swc_long",                       "바운딩박스 남서 경도"),
    ]
    
    f.write("  기존 스키마에 없는 FIT session 고유 필드:\n\n")
    for field, desc in new_session_fields:
        f.write(f"    + {field:<40} {desc}\n")
    f.write(f"\n  → activities 테이블에 추가 필요: {len(new_session_fields)}개 필드\n\n")
    
    # ── A5: lap 필드 → activity_laps 테이블 보강 ──
    f.write("─" * 70 + "\n")
    f.write("  A5. FIT lap 필드 → activity_laps 테이블 대폭 보강\n")
    f.write("─" * 70 + "\n\n")
    f.write(f"  기존 TCX lap: ~12개 필드\n")
    f.write(f"  FIT lap: {len(FIT_LAP_KNOWN)}개 알려진 필드\n\n")
    f.write("  추가 필드 (TCX 대비):\n")
    
    tcx_lap_fields = {"start_time", "total_time", "total_distance", "max_speed",
                      "calories", "avg_heart_rate", "max_heart_rate", "intensity",
                      "trigger_method", "avg_cadence", "avg_speed"}
    
    fit_only_lap = [f for f in FIT_LAP_KNOWN if f not in tcx_lap_fields]
    for field in sorted(fit_only_lap)[:30]:
        f.write(f"    + {field}\n")
    if len(fit_only_lap) > 30:
        f.write(f"    ... 외 {len(fit_only_lap) - 30}개\n")
    f.write(f"\n  → activity_laps 테이블 대폭 확장 필요 (12 → ~70개 컬럼)\n\n")
    
    # ── A6: 데이터 소스별 최종 비교표 ──
    f.write("─" * 70 + "\n")
    f.write("  A6. 최종 데이터 소스 비교 (수정본)\n")
    f.write("─" * 70 + "\n\n")
    
    f.write(f"  {'항목':<25} {'Strava CSV':>12} {'Strava FIT':>12} {'Garmin CSV':>12} {'Intervals':>12}\n")
    f.write(f"  {'─'*25} {'─'*12} {'─'*12} {'─'*12} {'─'*12}\n")
    f.write(f"  {'활동 요약 컬럼':<25} {'101':>12} {'132(session)':>12} {'38':>12} {'86':>12}\n")
    f.write(f"  {'시계열 필드':<25} {'(없음)':>12} {'29(record)':>12} {'(없음)':>12} {'(없음)':>12}\n")
    f.write(f"  {'랩 필드':<25} {'(없음)':>12} {'97(lap)':>12} {'(없음)':>12} {'(없음)':>12}\n")
    f.write(f"  {'활동 수':<25} {'489':>12} {'355':>12} {'320':>12} {'534':>12}\n")
    f.write(f"  {'활동 파일':<25} {'487':>12} {'(포함)':>12} {'(없음)':>12} {'(없음)':>12}\n")
    f.write(f"  {'러닝 다이내믹스':<25} {'✗':>12} {'✓(6필드)':>12} {'✓(4컬럼)':>12} {'✗':>12}\n")
    f.write(f"  {'파워 데이터':<25} {'✓(3컬럼)':>12} {'✓(5필드)':>12} {'✓(4컬럼)':>12} {'✓(11컬럼)':>12}\n")
    f.write(f"  {'HR 존 데이터':<25} {'✗':>12} {'✗':>12} {'✗':>12} {'✓(14컬럼)':>12}\n")
    f.write(f"  {'파워 존 데이터':<25} {'✗':>12} {'✗':>12} {'✗':>12} {'✓(8컬럼)':>12}\n")
    f.write(f"  {'날씨':<25} {'✓(6컬럼)':>12} {'온도만':>12} {'✓(2컬럼)':>12} {'✗':>12}\n")
    f.write("\n")
    
    # ── A7: 스키마 수정 권고 ──
    f.write("─" * 70 + "\n")
    f.write("  A7. Superset 스키마 v2 수정 권고사항\n")
    f.write("─" * 70 + "\n\n")
    f.write("  1) activity_streams 테이블: +11개 컬럼\n")
    f.write("     power, accumulated_power, temperature,\n")
    f.write("     vertical_oscillation, vertical_ratio,\n")
    f.write("     stance_time, stance_time_balance, stance_time_percent,\n")
    f.write("     step_length, fractional_cadence, activity_type\n\n")
    f.write("  2) activities 테이블: +31개 컬럼 (FIT session 고유)\n")
    f.write("     threshold_power, training_stress_score, intensity_factor,\n")
    f.write("     total_training_effect, total_anaerobic_training_effect,\n")
    f.write("     avg/max stance_time/balance/percent, step_length,\n")
    f.write("     vertical_oscillation/ratio, torque_effectiveness,\n")
    f.write("     pedal_smoothness, left_right_balance, normalized_power,\n")
    f.write("     total_work/strides/moving_time/fat_calories,\n")
    f.write("     min_heart_rate, temperature, bounding_box 좌표\n\n")
    f.write("  3) activities 테이블: +8개 컬럼 (Garmin CSV 누락분)\n")
    f.write("     favorite, title, aerobic_training_effect, avg_gap,\n")
    f.write("     steps, decompression, best_lap, num_laps\n\n")
    f.write("  4) activities 테이블: +41개 컬럼 (Intervals CSV 누락분)\n")
    f.write("     HR존 경계/시간 14개, 파워존 시간 8개,\n")
    f.write("     부하분리 3개, eftp/variability/efficiency,\n")
    f.write("     fatigue/fitness, weight/resting_hr/lthr,\n")
    f.write("     trainer/race/sub_type/rpe, ignore 플래그 3개\n\n")
    f.write("  5) activity_laps 테이블: 12 → ~70개 컬럼 확장\n")
    f.write("     FIT lap 데이터 전면 반영\n\n")
    f.write("  6) activity_zones 테이블 신설 (HR존/파워존 분리 저장)\n\n")
    f.write("  → 다음 단계: Superset 스키마 v2 DDL 생성 (Step 3 완료)\n")

print(f"✅ 보고서 Addendum 추가: {REPORT_PATH}")

# ── JSON 업데이트 ──
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    inventory = json.load(f)

inventory["Strava_FIT"] = {
    "total_files": 355,
    "size_min": 230,
    "size_max": 453522,
    "size_avg": 55050,
    "record_fields": list(FIT_RECORD_FIELDS.keys()),
    "record_field_count": len(FIT_RECORD_FIELDS),
    "session_known_fields": FIT_SESSION_KNOWN,
    "session_known_count": len(FIT_SESSION_KNOWN),
    "session_total_with_unknown": 132,
    "lap_known_fields": FIT_LAP_KNOWN,
    "lap_known_count": len(FIT_LAP_KNOWN),
    "lap_total_with_unknown": 97,
}

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 인벤토리 업데이트: {JSON_PATH}")

# 최종 통계
print()
print("=" * 60)
print("  최종 데이터 소스 통계")
print("=" * 60)
print(f"  Strava CSV:      101 컬럼,  489 행")
print(f"  Strava FIT:      record 29필드, session 132필드, lap 97필드 × 355파일")
print(f"  Strava TCX:      129 파일 (GPX 3파일)")
print(f"  Garmin CSV:       38 컬럼,  320 행 (100% fill)")
print(f"  Intervals CSV:    86 컬럼,  534 행")
print(f"  ─────────────────────────────────")
print(f"  Superset 스키마 예상:")
print(f"    activities:     ~180+ 컬럼 (모든 소스 합산)")
print(f"    activity_streams: ~20 컬럼 (FIT record 기반)")
print(f"    activity_laps:   ~70 컬럼 (FIT lap 기반)")
print(f"    activity_zones:  신설 (HR/파워 존)")

