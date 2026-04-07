#!/usr/bin/env python3
"""데이터 마스터 시트 자동 생성 v3.

SSOT: src/utils/metric_registry.py (MetricDef + METRIC_CATEGORIES)
보조: src/db_setup.py (DDL — Layer 3/4 테이블, 제약조건)

출력: v0.3/data/data_master.md

사용법:
    python scripts/gen_data_master.py
"""
import re
import sys
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "v0.3" / "data" / "data_master.md"


# ─────────────────────────────────────────────
# 1. SSOT 로드
# ─────────────────────────────────────────────

from src.utils.metric_registry import (
    METRIC_REGISTRY, METRIC_CATEGORIES, get_by_storage, get_by_category
)


# ─────────────────────────────────────────────
# 2. DDL 파싱 (Layer 3/4 + 제약조건용)
# ─────────────────────────────────────────────

def parse_db_setup():
    """db_setup.py에서 테이블/컬럼 파싱."""
    path = ROOT / "src" / "db_setup.py"
    text = path.read_text(encoding="utf-8")
    tables = OrderedDict()
    pattern = re.compile(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\);',
        re.DOTALL | re.IGNORECASE
    )
    for m in pattern.finditer(text):
        tname = m.group(1)
        body = m.group(2)
        cols = []
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            if re.match(r'^(UNIQUE|FOREIGN|CHECK|CONSTRAINT|PRIMARY KEY)\b', line, re.IGNORECASE):
                continue
            col_match = re.match(r'^(\w+)\s+(INTEGER|TEXT|REAL|BLOB)', line, re.IGNORECASE)
            if col_match:
                cols.append({"name": col_match.group(1), "dtype": col_match.group(2).upper()})
        tables[tname] = cols

    view_pattern = re.compile(r'CREATE\s+VIEW\s+IF\s+NOT\s+EXISTS\s+(\w+)', re.IGNORECASE)
    for m in view_pattern.finditer(text):
        tables[m.group(1)] = []
    return tables


# ─────────────────────────────────────────────
# 3. 교차 검증
# ─────────────────────────────────────────────

def cross_validate(ddl_tables):
    """SSOT vs DDL 불일치 검출."""
    issues = []

    # activity_summaries 컬럼 검증
    registry_as = {md.name for md in get_by_storage("activity_summary")}
    ddl_as = {c["name"] for c in ddl_tables.get("activity_summaries", [])}
    mgmt_cols = {"id", "source", "source_id", "matched_group_id", "created_at", "updated_at"}
    # DDL에서 관리 컬럼 + 제거 예정 6개 제외
    pending_remove = {"calories", "normalized_power", "suffer_score",
                      "training_effect_aerobic", "training_effect_anaerobic", "training_load"}
    ddl_data = ddl_as - mgmt_cols - pending_remove
    only_registry = registry_as - ddl_data
    only_ddl = ddl_data - registry_as
    if only_registry:
        issues.append(f"🔴 activity_summaries: SSOT에만 존재 — {', '.join(sorted(only_registry))}")
    if only_ddl:
        issues.append(f"🔴 activity_summaries: DDL에만 존재 — {', '.join(sorted(only_ddl))}")
    if pending_remove & ddl_as:
        issues.append(f"🟠 activity_summaries: 제거 예정 컬럼 아직 DDL에 존재 — {', '.join(sorted(pending_remove & ddl_as))}")

    # daily_wellness 컬럼 검증
    registry_wl = {md.name for md in get_by_storage("wellness")}
    ddl_wl = {c["name"] for c in ddl_tables.get("daily_wellness", [])}
    wl_mgmt = {"id", "date", "created_at", "updated_at"}
    ddl_wl_data = ddl_wl - wl_mgmt
    only_reg_wl = registry_wl - ddl_wl_data
    only_ddl_wl = ddl_wl_data - registry_wl
    if only_reg_wl:
        issues.append(f"🔴 daily_wellness: SSOT에만 존재 — {', '.join(sorted(only_reg_wl))}")
    if only_ddl_wl:
        issues.append(f"🔴 daily_wellness: DDL에만 존재 — {', '.join(sorted(only_ddl_wl))}")

    # daily_fitness 삭제 확인
    if "daily_fitness" in ddl_tables:
        issues.append("🟠 daily_fitness: 삭제 예정이나 DDL에 아직 존재")

    # 카테고리 검증
    cats_used = set(md.category for md in METRIC_REGISTRY.values())
    cats_defined = set(METRIC_CATEGORIES.keys()) - {"_unmapped"}
    if cats_used - cats_defined:
        issues.append(f"🔴 카테고리: 사용되나 미정의 — {', '.join(sorted(cats_used - cats_defined))}")
    if cats_defined - cats_used:
        issues.append(f"🟡 카테고리: 정의되나 미사용 — {', '.join(sorted(cats_defined - cats_used))}")

    return issues


# ─────────────────────────────────────────────
# 4. 마크다운 생성
# ─────────────────────────────────────────────

def generate():
    ddl_tables = parse_db_setup()
    issues = cross_validate(ddl_tables)

    lines = []
    lines.append("# RunPulse v0.3 데이터 마스터 시트")
    lines.append("")
    lines.append(f"> 자동 생성: `scripts/gen_data_master.py` | SSOT: `src/utils/metric_registry.py`")
    lines.append("")

    # ── 요약 ──
    total = len(METRIC_REGISTRY)
    by_storage = {}
    for md in METRIC_REGISTRY.values():
        by_storage.setdefault(md.storage, []).append(md)
    lines.append("## 요약")
    lines.append("")
    lines.append(f"- 전체 MetricDef: **{total}**")
    for s in ["activity_summary", "wellness", "metric"]:
        lines.append(f"  - {s}: {len(by_storage.get(s, []))}")
    lines.append(f"- 카테고리: **{len(METRIC_CATEGORIES) - 1}** (+ _unmapped)")
    lines.append(f"- DDL 테이블: **{len(ddl_tables)}**")
    lines.append(f"- 불일치: **{len(issues)}**")
    lines.append("")

    # ── 섹션 1: 카테고리 정의 ──
    lines.append("## 섹션 1: 카테고리 정의")
    lines.append("")
    lines.append("| category | 설명 | 메트릭 수 |")
    lines.append("|----------|------|-----------|")
    for cat, desc in METRIC_CATEGORIES.items():
        if cat == "_unmapped":
            continue
        count = len(get_by_category(cat))
        lines.append(f"| `{cat}` | {desc} | {count} |")
    lines.append("")

    # ── 섹션 2: Layer 1 — activity_summaries ──
    lines.append("## 섹션 2: Layer 1 — activity_summaries (storage=activity_summary)")
    lines.append("")
    lines.append("| column | category | unit | description |")
    lines.append("|--------|----------|------|-------------|")
    for md in sorted(get_by_storage("activity_summary"), key=lambda m: m.name):
        lines.append(f"| `{md.name}` | {md.category} | {md.unit} | {md.description} |")
    lines.append("")

    # ── 섹션 3: Layer 1 — daily_wellness ──
    lines.append("## 섹션 3: Layer 1 — daily_wellness (storage=wellness)")
    lines.append("")
    lines.append("| column | category | unit | description | scope |")
    lines.append("|--------|----------|------|-------------|-------|")
    for md in sorted(get_by_storage("wellness"), key=lambda m: m.name):
        lines.append(f"| `{md.name}` | {md.category} | {md.unit} | {md.description} | {md.scope} |")
    lines.append("")

    # ── 섹션 4: Layer 2 — metric_store ──
    lines.append("## 섹션 4: Layer 2 — metric_store (storage=metric)")
    lines.append("")

    metric_defs = sorted(get_by_storage("metric"), key=lambda m: (m.category, m.scope, m.name))
    current_cat = None
    lines.append("| metric_name | category | scope | unit | description | aliases |")
    lines.append("|-------------|----------|-------|------|-------------|---------|")
    for md in metric_defs:
        alias_str = ", ".join(f"{s}:`{r}`" for s, r in md.aliases.items()) if md.aliases else ""
        cat_marker = f"**{md.category}**" if md.category != current_cat else md.category
        current_cat = md.category
        lines.append(f"| `{md.name}` | {cat_marker} | {md.scope} | {md.unit} | {md.description} | {alias_str} |")
    lines.append("")

    # ── 섹션 5: Layer 3/4 테이블 (DDL only) ──
    lines.append("## 섹션 5: Layer 3/4 테이블 (DDL 관리)")
    lines.append("")
    layer3_4 = ["activity_streams", "activity_laps", "activity_best_efforts",
                "gear", "weather_cache", "sync_jobs",
                "chat_messages", "goals", "planned_workouts",
                "user_training_prefs", "session_outcomes"]
    for tname in layer3_4:
        cols = ddl_tables.get(tname, [])
        lines.append(f"### `{tname}` ({len(cols)} cols)")
        lines.append("")
        if cols:
            lines.append("| column | dtype |")
            lines.append("|--------|-------|")
            for c in cols:
                lines.append(f"| `{c['name']}` | {c['dtype']} |")
        else:
            lines.append("*(DDL에서 발견되지 않음)*")
        lines.append("")

    # ── 섹션 6: 뷰 ──
    views = [t for t in ddl_tables if t.startswith("v_")]
    if views:
        lines.append("## 섹션 6: 뷰")
        lines.append("")
        for v in views:
            lines.append(f"- `{v}`")
        lines.append("")

    # ── 섹션 7: 불일치 ──
    lines.append("## 섹션 7: 불일치 검출")
    lines.append("")
    if issues:
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("✅ 불일치 없음")
    lines.append("")

    # ── 섹션 8: scope × category 교차표 ──
    lines.append("## 섹션 8: scope × category 교차표")
    lines.append("")
    scopes = ["activity", "daily", "weekly", "athlete"]
    cats = sorted(set(md.category for md in METRIC_REGISTRY.values()))
    header = "| category | " + " | ".join(scopes) + " | total |"
    sep = "|----------|" + "|".join(["------"] * len(scopes)) + "|-------|"
    lines.append(header)
    lines.append(sep)
    for cat in cats:
        counts = []
        for s in scopes:
            n = len([md for md in METRIC_REGISTRY.values() if md.category == cat and md.scope == s])
            counts.append(str(n) if n else "")
        total_cat = len(get_by_category(cat))
        lines.append(f"| `{cat}` | " + " | ".join(counts) + f" | **{total_cat}** |")
    lines.append("")

    # ── 섹션 9: storage × category 교차표 ──
    lines.append("## 섹션 9: storage × category 교차표")
    lines.append("")
    storages = ["activity_summary", "wellness", "metric"]
    header2 = "| category | " + " | ".join(storages) + " | total |"
    sep2 = "|----------|" + "|".join(["------"] * len(storages)) + "|-------|"
    lines.append(header2)
    lines.append(sep2)
    for cat in cats:
        counts2 = []
        for st in storages:
            n = len([md for md in METRIC_REGISTRY.values() if md.category == cat and md.storage == st])
            counts2.append(str(n) if n else "")
        total_cat = len(get_by_category(cat))
        lines.append(f"| `{cat}` | " + " | ".join(counts2) + f" | **{total_cat}** |")
    lines.append("")

    # 쓰기
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT} ({len(lines)} lines)")
    print(f"  MetricDefs: {total}")
    print(f"  Categories: {len(METRIC_CATEGORIES) - 1}")
    print(f"  DDL tables: {len(ddl_tables)}")
    print(f"  Issues: {len(issues)}")


if __name__ == "__main__":
    generate()
