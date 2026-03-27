"""용어집/가이드 페이지 — 메트릭 설명 + 분류 기준 + 적정 범위 통합.

/guide : 전체 용어집
/guide#메트릭명 : 특정 메트릭으로 스크롤
"""
from __future__ import annotations

import html as _html

from flask import Blueprint

from src.metrics.workout_classifier import TAG_COLORS, TAG_LABELS, _EFFECTS
from src.web.helpers import METRIC_DESCRIPTIONS, html_page

guide_bp = Blueprint("guide", __name__)


# 메트릭별 상세 정보 (적정 범위, 해석)
_METRIC_DETAILS: dict[str, dict] = {
    "UTRS": {"range": "0~100", "good": "70+", "warn": "40~70", "bad": "<40",
             "detail": "웰니스(HRV, 수면, BB)·피트니스(CTL, TSB)·부하(ACWR)를 종합한 훈련 준비도. "
                       "70 이상이면 고강도 훈련 가능, 40 미만이면 휴식 권장."},
    "CIRS": {"range": "0~100", "good": "<25", "warn": "25~50", "bad": ">50",
             "detail": "ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1로 계산. "
                       "25 이하 안전, 50 이상 부상 위험 증가, 75 이상 즉시 훈련 중단 권장."},
    "ACWR": {"range": "0~3+", "good": "0.8~1.3", "warn": "1.3~1.5 또는 <0.8", "bad": ">1.5",
             "detail": "7일 평균 TRIMP / 28일 평균 TRIMP. 0.8~1.3이 Sweet Spot. "
                       "1.5 이상이면 급격한 부하 증가로 부상 위험."},
    "RTTI": {"range": "0~200+", "good": "70~100", "warn": "100~130", "bad": ">130",
             "detail": "ATL/(CTL×웰니스보정). 100이면 적정 훈련량, 130+ 과부하. "
                       "Garmin Running Tolerance 데이터 있으면 우선 사용."},
    "LSI": {"range": "0~5+", "good": "<1.0", "warn": "1.0~1.5", "bad": ">1.5",
            "detail": "오늘 TRIMP / 21일 평균 TRIMP. 1.0 이하 안정, 1.5 초과 급격한 부하 증가."},
    "Monotony": {"range": "0~5+", "good": "<1.5", "warn": "1.5~2.0", "bad": ">2.0",
                 "detail": "7일 TRIMP 평균/표준편차. 낮을수록 훈련 강도 변화가 다양. "
                           "2.0 이상이면 매일 비슷한 강도로 훈련 → 과훈련 위험."},
    "Strain": {"range": "0~1000+", "good": "<200", "warn": "200~400", "bad": ">400",
               "detail": "주간 TRIMP × Monotony. Monotony가 높을 때 Strain이 급증. "
                         "400 이상이면 회복 기간 필요."},
    "TSB": {"range": "-50~+30", "good": "-10~+10", "warn": "-30~-10", "bad": "<-30 또는 >+25",
            "detail": "CTL - ATL. 양수면 신선(회복), 음수면 피로 축적. "
                      "-10~+10 최적 훈련. CTL/ATL은 Intervals.icu 또는 자체 계산(DailyTRIMP EMA)."},
    "EF": {"range": "0.5~3.0", "good": ">1.5", "warn": "1.0~1.5", "bad": "<1.0",
           "detail": "속도(m/s) / 심박수. 같은 HR에서 더 빠르면 EF 상승 → 체력 향상 의미. "
                     "시간 경과에 따른 추세가 중요."},
    "Decoupling": {"range": "0~30%", "good": "<5%", "warn": "5~10%", "bad": ">10%",
                   "detail": "전반/후반 HR:페이스 비율 차이. 5% 이하면 유산소 기반 양호. "
                             "10% 이상이면 지구력 부족 → 장거리 훈련 필요."},
    "VDOT": {"range": "20~85", "good": "-", "warn": "-", "bad": "-",
             "detail": "Jack Daniels VDOT. ①최근 레이스 기록(8주 이내, FEARP 환경 보정) "
                       "②고강도 활동 가중 평균 ③Runalyze/Garmin. "
                       "보정(VDOT_ADJ): Strava stream 역치 HR 구간 페이스 기반 (±3~7%)."},
    "DI": {"range": "0~100", "good": ">70", "warn": "40~70", "bad": "<40",
           "detail": "90분+ 장거리 러닝에서 후반부 페이스 유지 비율. "
                     "70 이상 우수, 40 미만 장거리 훈련 필요. "
                     "DARP 보정: 5K 0%, 10K 최대 2%, 하프 5%, 풀 10%."},
    "FEARP": {"range": "페이스 (sec/km)", "good": "-", "warn": "-", "bad": "-",
              "detail": "기온(15°C 이상 +0.4%/°C), 습도(50% 이상 +0.1%/%), "
                        "고도(+0.011%/m), 경사도를 반영한 보정 페이스."},
    "eFTP": {"range": "페이스 (sec/km)", "good": "-", "warn": "-", "bad": "-",
             "detail": "약 60분 유지 가능한 역치 페이스. VDOT_ADJ 기반 Daniels T-pace 우선, "
                       "Intervals FTP fallback. 현재 체력 기준 역치."},
    "REC": {"range": "0~100", "good": ">60", "warn": "30~60", "bad": "<30",
            "detail": "EF × (1-Dec%) × 폼팩터. 7일 평균 기반. "
                      "높을수록 같은 노력으로 더 빠르게 달릴 수 있는 상태."},
    "TEROI": {"range": "-5~+5", "good": ">0", "warn": "-1~0", "bad": "<-1",
              "detail": "CTL 변화량 / 총 TRIMP × 1000 (28일). 양수면 효율적 훈련, "
                        "음수면 투입 대비 피트니스 하락."},
    "RRI": {"range": "0~100", "good": ">80", "warn": "60~80", "bad": "<60",
            "detail": "VDOT진행률 × CTL충족률 × DI × (100-CIRS)/100. "
                      "80 이상 레이스 준비 완료, 60 미만 추가 훈련 필요."},
    "SAPI": {"range": "50~150%", "good": "95~105%", "warn": "80~95% 또는 105~120%", "bad": "<80%",
             "detail": "기준 기온(10~15°C) FEARP 대비 현재 FEARP 비율. "
                       "100%=동일, 100% 미만=더운 날씨로 성능 저하."},
    "RMR": {"range": "0~100", "good": ">70", "warn": "40~70", "bad": "<40",
            "detail": "유산소용량/역치강도/지구력/동작효율성/회복력 5축 레이더. "
                      "각 축 0~100, 종합 평균. 28일 기준."},
    "MarathonShape": {"range": "0~100%", "good": ">80%", "warn": "50~80%", "bad": "<50%",
                      "detail": "5요소 종합: 주간 볼륨(35%) + 최장 거리(20%) + 장거리 빈도(20%) "
                                "+ 일관성(15%) + 페이스 품질(10%). 거리별 목표 차등 "
                                "(마라톤: 주 60~80km, 장거리 28~37km, 25km+ 6회). "
                                "80%+ 레이스 준비 충분."},
}


@guide_bp.route("/guide")
def guide_page():
    """용어집/가이드 페이지."""
    body = _render_guide()
    return html_page("용어집 · 가이드", body, active_tab="settings")


def _render_guide() -> str:
    """가이드 페이지 HTML 생성."""
    parts = [
        "<div style='max-width:800px;margin:0 auto;'>",
        "<h1 style='font-size:1.3rem;margin-bottom:0.5rem;'>📖 RunPulse 용어집 · 가이드</h1>",
        "<p class='muted' style='margin-bottom:1.5rem;'>메트릭 설명, 적정 범위, 운동 분류 기준</p>",
    ]

    # 운동 분류 섹션
    parts.append("<h2 id='workout-type' style='font-size:1.1rem;margin:1.5rem 0 0.5rem;"
                 "border-bottom:1px solid var(--card-border);padding-bottom:0.3rem;'>"
                 "🏃 운동 유형 분류</h2>")
    parts.append("<div class='card'><table style='width:100%;font-size:0.85rem;'>"
                 "<thead><tr><th>분류</th><th>기준</th><th>훈련 효과</th></tr></thead><tbody>")
    _CRITERIA = {
        "easy": "Z1-2 > 70%",
        "tempo": "Z3 > 30%, HR 75~88%",
        "threshold": "페이스 ≈ eFTP ±5%, Z3-4",
        "interval": "Z4-5 > 25%",
        "long": "90분+ 또는 15km+, Z1-2 위주",
        "race": "HR > 90% maxHR, 5km+, Z4-5",
        "recovery": "5km 미만, 40분 미만, Z1-2 > 85%",
    }
    for wtype in ["easy", "tempo", "threshold", "interval", "long", "race", "recovery"]:
        color = TAG_COLORS.get(wtype, "#888")
        label = TAG_LABELS.get(wtype, wtype)
        effect = _EFFECTS.get(wtype, "")
        criteria = _CRITERIA.get(wtype, "")
        parts.append(f"<tr><td style='color:{color};font-weight:600;'>{label}</td>"
                     f"<td>{criteria}</td><td>{effect}</td></tr>")
    parts.append("</tbody></table>"
                 "<p class='muted' style='margin:0.5rem 0 0;font-size:0.78rem;'>"
                 "RunPulse가 HR존·페이스·거리·시간을 분석하여 자동 분류합니다.</p></div>")

    # 메트릭 상세 섹션
    parts.append("<h2 style='font-size:1.1rem;margin:1.5rem 0 0.5rem;"
                 "border-bottom:1px solid var(--card-border);padding-bottom:0.3rem;'>"
                 "📊 메트릭 상세</h2>")

    for name, desc in METRIC_DESCRIPTIONS.items():
        detail = _METRIC_DETAILS.get(name, {})
        range_str = detail.get("range", "")
        good = detail.get("good", "")
        warn = detail.get("warn", "")
        bad = detail.get("bad", "")
        detail_text = detail.get("detail", desc)

        range_row = ""
        if good and good != "-":
            range_row = (
                f"<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.3rem;font-size:0.78rem;'>"
                f"<span style='color:var(--green);'>적정: {_html.escape(good)}</span>"
                f"<span style='color:var(--orange);'>주의: {_html.escape(warn)}</span>"
                f"<span style='color:var(--red);'>위험: {_html.escape(bad)}</span>"
                f"</div>"
            )

        parts.append(
            f"<div id='{_html.escape(name)}' class='card' style='padding:0.8rem 1rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<h3 style='margin:0;font-size:0.95rem;'>{_html.escape(name)}</h3>"
            f"<span class='muted' style='font-size:0.78rem;'>{_html.escape(range_str)}</span></div>"
            f"<p style='margin:0.3rem 0 0;font-size:0.85rem;color:var(--secondary);'>"
            f"{_html.escape(detail_text)}</p>"
            f"{range_row}</div>"
        )

    parts.append("</div>")
    return "\n".join(parts)
