#!/usr/bin/env python3
"""메트릭 사전 (metric_dictionary.md) 자동 생성.

사용법:
    python scripts/gen_metric_dictionary.py

ALL_CALCULATORS + SEMANTIC_GROUPS에서 메타데이터를 추출하여
v0.3/data/metric_dictionary.md를 생성합니다.

calculator가 추가/변경되면 이 스크립트를 재실행하세요.
test_doc_sync.py가 불일치를 자동 감지합니다.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.metrics.engine import ALL_CALCULATORS
from src.utils.metric_groups import SEMANTIC_GROUPS

OUTPUT = ROOT / "v0.3" / "data" / "metric_dictionary.md"

RANGE_MEANINGS = {
    'recovery': '회복 수준', 'easy': '쉬운 강도', 'moderate': '보통',
    'hard': '높은 강도', 'very_hard': '매우 높은 강도',
    'excellent': '우수', 'good': '양호', 'fair': '보통', 'poor': '미흡',
    'beginner': '초보', 'intermediate': '중급', 'advanced': '상급', 'elite': '엘리트',
    'low': '낮음', 'normal': '정상', 'high': '높음', 'very_high': '매우 높음',
    'optimal': '최적', 'caution': '주의', 'danger': '위험',
    'varied': '다양함', 'monotonous': '단조로움',
    'elevated': '상승', 'spike': '급증',
    'declining': '하락', 'stable': '안정', 'building': '상승 중',
    'consistent': '일관됨', 'large': '큰 격차',
    'under': '여유', 'overload': '과부하',
    'insufficient': '부족', 'base': '기초', 'ready': '준비됨', 'peak': '피크',
    'rest': '휴식 필요', 'easy_only': '가벼운 운동만', 'full': '전면 훈련 가능',
    'boost': '고강도 가능', 'critical': '위험', 'negative': '음수',
}


def generate() -> str:
    """메트릭 사전 markdown 문자열 생성."""
    lines = []
    from datetime import date
    today = date.today().isoformat()
    n_calc = len(ALL_CALCULATORS)
    n_groups = len(SEMANTIC_GROUPS)

    lines.append("# RunPulse Metric Dictionary")
    lines.append("")
    lines.append(f"> 자동 생성: {today} | {n_calc} calculators | {n_groups} semantic groups")
    lines.append(">")
    lines.append("> 이 문서는 RunPulse가 계산하는 모든 메트릭의 정의, 해석, 범위를 정리한 공식 사전입니다.")
    lines.append("> UI 툴팁, AI 코칭 프롬프트, 사용자 도움말의 원본(single source of truth)으로 사용됩니다.")
    lines.append(">")
    lines.append("> **이 파일을 직접 수정하지 마세요.** `python scripts/gen_metric_dictionary.py`로 재생성합니다.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Part 1: 데이터 흐름
    lines.append("## 1. 데이터 흐름 개요")
    lines.append("")
    lines.append("```")
    lines.append("Garmin/Strava/Intervals/Runalyze")
    lines.append("        |")
    lines.append("        v")
    lines.append("  [Extractors] --- raw JSON ---> source_payloads (Layer 0)")
    lines.append("        |")
    lines.append("        v")
    lines.append("  activity_summaries (Layer 1)     daily_wellness (Layer 1)")
    lines.append("        |                                |")
    lines.append("        v                                v")
    lines.append("  metric_store (Layer 2) <--- CalcContext API <--- Calculators")
    lines.append("        |")
    lines.append("        v")
    lines.append("  [UI / AI Coach / API]")
    lines.append("```")
    lines.append("")
    lines.append("모든 RunPulse 메트릭은 `metric_store` 테이블에 `provider=runpulse:formula_v1`로 저장됩니다.")
    lines.append("소스(Garmin 등)가 제공하는 원본 메트릭도 같은 테이블에 각 소스 provider로 저장되며,")
    lines.append("`is_primary=1` 플래그로 대표값이 선택됩니다.")
    lines.append("")
    lines.append("---")
    lines.append("")

    activity_calcs = [c for c in ALL_CALCULATORS if c.scope_type == "activity"]
    daily_calcs = [c for c in ALL_CALCULATORS if c.scope_type == "daily"]

    def write_calc_section(calc):
        display = getattr(calc, 'display_name', calc.name)
        desc = getattr(calc, 'description', '')
        unit = getattr(calc, 'unit', '')
        ranges = getattr(calc, 'ranges', None)
        hib = getattr(calc, 'higher_is_better', None)
        produces = ', '.join([f'`{p}`' for p in calc.produces])
        dep = ', '.join([f'`{r}`' for r in calc.requires]) if calc.requires else '소스 데이터 직접 사용'

        lines.append(f"### {display}")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 메트릭 이름 | {produces} |")
        lines.append(f"| 설명 | {desc} |")
        lines.append(f"| 단위 | {unit if unit else '무차원'} |")
        lines.append(f"| 카테고리 | `{calc.category}` |")
        lines.append(f"| 의존성 | {dep} |")
        if hib is True:
            lines.append("| 해석 | 높을수록 좋음 |")
        elif hib is False:
            lines.append("| 해석 | 낮을수록 좋음 |")
        lines.append("")

        if ranges and isinstance(ranges, dict):
            lines.append("**범위 해석:**")
            lines.append("")
            lines.append("| 등급 | 범위 | 의미 |")
            lines.append("|------|------|------|")
            for label, vals in ranges.items():
                meaning = RANGE_MEANINGS.get(label, label)
                if isinstance(vals, list) and len(vals) == 2:
                    lines.append(f"| {label} | {vals[0]} ~ {vals[1]} | {meaning} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Part 2: Activity-scope
    lines.append(f"## 2. Activity-Scope 메트릭 ({len(activity_calcs)}개)")
    lines.append("")
    lines.append("운동이 기록될 때마다 계산되는 메트릭입니다.")
    lines.append("")
    for calc in activity_calcs:
        write_calc_section(calc)

    # Part 3: Daily-scope
    lines.append(f"## 3. Daily-Scope 메트릭 ({len(daily_calcs)}개)")
    lines.append("")
    lines.append("매일 최근 활동과 웰니스 데이터를 종합하여 계산됩니다.")
    lines.append("")
    for calc in daily_calcs:
        write_calc_section(calc)

    # Part 4: 시맨틱 그룹
    lines.append(f"## 4. 시맨틱 그룹 ({n_groups}개)")
    lines.append("")
    lines.append("같은 개념을 측정하는 여러 소스/메트릭을 하나의 그룹으로 묶어 UI에서 비교 뷰를 제공합니다.")
    lines.append("")
    for gname, gdata in SEMANTIC_GROUPS.items():
        display = gdata["display_name"]
        members = gdata["members"]
        strategy = gdata["primary_strategy"]
        lines.append(f"### {display} (`{gname}`)")
        lines.append("")
        lines.append(f"표시 전략: **{strategy}**")
        lines.append("")
        lines.append("| 메트릭 | 제공자 |")
        lines.append("|--------|--------|")
        for mname, mprov in members:
            lines.append(f"| `{mname}` | {mprov} |")
        lines.append("")

    # Part 5: 의존성 그래프
    lines.append("## 5. 계산 의존성 그래프")
    lines.append("")
    lines.append("```")
    lines.append("Activity-scope:")
    for c in activity_calcs:
        req = ' + '.join(c.requires) if c.requires else '(소스 직접)'
        prod = ', '.join(c.produces)
        lines.append(f"  {req} --> {prod}")
    lines.append("")
    lines.append("Daily-scope:")
    for c in daily_calcs:
        req = ' + '.join(c.requires) if c.requires else '(소스 직접)'
        prod = ', '.join(c.produces)
        lines.append(f"  {req} --> {prod}")
    lines.append("```")
    lines.append("")

    # Part 6: 카테고리 분류
    lines.append("## 6. 카테고리 분류")
    lines.append("")
    categories = {}
    for calc in ALL_CALCULATORS:
        cat = calc.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].extend(calc.produces)
    cat_labels = {
        'rp_load': '훈련 부하', 'rp_efficiency': '러닝 효율성',
        'rp_performance': '성과 지표', 'rp_classification': '운동 분류',
        'rp_readiness': '훈련 준비도', 'rp_risk': '부상 위험',
        'rp_endurance': '내구성', 'rp_prediction': '레이스 예측',
        'rp_distribution': '강도 분포', 'rp_recovery': '회복 상태',
        'rp_trend': '훈련 추세',
    }
    lines.append("| 카테고리 | 한글명 | 포함 메트릭 |")
    lines.append("|----------|--------|------------|")
    for cat, metrics in sorted(categories.items()):
        label = cat_labels.get(cat, cat)
        mlist = ', '.join([f'`{m}`' for m in metrics])
        lines.append(f"| `{cat}` | {label} | {mlist} |")
    lines.append("")

    # Part 7: 소스 메트릭
    lines.append("## 7. 소스별 원본 메트릭 (참고)")
    lines.append("")
    lines.append("RunPulse가 계산하는 메트릭 외에, 각 소스가 제공하는 원본 메트릭도 `metric_store`에 저장됩니다.")
    lines.append("")
    lines.append("| 소스 | 주요 메트릭 예시 |")
    lines.append("|------|-----------------|")
    lines.append("| Garmin | `vo2max_activity`, `training_readiness`, `body_battery_high/low`, `training_load` |")
    lines.append("| Strava | `suffer_score`, `perceived_exertion`, `achievement_count` |")
    lines.append("| Intervals.icu | `training_load_score`, `efficiency_factor`, `icu_ftp`, `decoupling` |")
    lines.append("| Runalyze | `effective_vo2max`, `marathon_shape` |")
    lines.append("")

    return '\n'.join(lines)


def get_structural_fingerprint() -> dict:
    """문서 동기화 검증용 구조적 핑거프린트 생성.
    
    날짜 같은 변동값을 제외하고, calculator 수/이름/그룹 수 등
    구조적 정보만 추출합니다.
    """
    calc_names = sorted([c.name for c in ALL_CALCULATORS])
    group_names = sorted(SEMANTIC_GROUPS.keys())
    produces_all = sorted(set(
        p for c in ALL_CALCULATORS for p in c.produces
    ))
    return {
        "calculator_count": len(ALL_CALCULATORS),
        "calculator_names": calc_names,
        "group_count": len(SEMANTIC_GROUPS),
        "group_names": group_names,
        "produces": produces_all,
    }


if __name__ == "__main__":
    content = generate()
    OUTPUT.write_text(content, encoding="utf-8")
    n_lines = len(content.splitlines())
    print(f"Generated {OUTPUT.relative_to(ROOT)} ({n_lines} lines)")
    fp = get_structural_fingerprint()
    print(f"  Calculators: {fp['calculator_count']}")
    print(f"  Groups: {fp['group_count']}")
    print(f"  Produces: {len(fp['produces'])} metrics")
