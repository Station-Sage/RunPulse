#!/usr/bin/env python3
"""RunPulse 데이터 정합성 검증 v1.5

SSOT (metric_registry.py) ↔ DDL (db_setup.py) ↔ 실제 DB ↔ 설계문서 ↔ Extractor 교차 검증.

검증 항목:
  1. SSOT activity_summary ↔ DDL
  2. SSOT wellness ↔ DDL
  3. daily_fitness 삭제 여부
  4. 카테고리 정합성 (SSOT 내)
  5. MetricDef 필드 유효성
  6. MetricDef 중복 이름
  7. alias 충돌
  8. scope 일관성
  9. 실제 DB 검증 (선택)
 10. Extractor _metric() category 값 검증 (16-domain 기준)
 11. Extractor _metric() 미등록 메트릭 이름 검출
 12. Extractor _metric() 폐기 예정 메트릭 이름 검출
 13. Garmin wellness entity_type 이름 일관성 (wellness_* 설계 spec)
 14. Calculator category 속성 16-domain 준수 (rp_* 등 구버전 방지)
 15. Calculator produces ↔ METRIC_REGISTRY 등록 일치
 16. DataValidator _check_* 메서드 수 (설계: 12개) 및 CheckResult 필드 정합성

사용법:
    python scripts/check_data_consistency.py [--db PATH]

종료 코드:
    0 = 모든 검증 통과
    1 = 경고만 (🟠🟡)
    2 = 오류 있음 (🔴)
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.metric_registry import (
    METRIC_REGISTRY, METRIC_CATEGORIES, get_by_storage, MetricDef
)


# ─────────────────────────────────────────────
# 1. DDL 파싱
# ─────────────────────────────────────────────

def parse_ddl_tables() -> dict[str, list[str]]:
    """db_setup.py에서 테이블명 → 컬럼명 리스트."""
    path = ROOT / "src" / "db_setup.py"
    text = path.read_text(encoding="utf-8")
    tables = {}
    pattern = re.compile(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\);',
        re.DOTALL | re.IGNORECASE
    )
    for m in pattern.finditer(text):
        tname = m.group(1)
        cols = []
        for line in m.group(2).split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            if re.match(r'^(UNIQUE|FOREIGN|CHECK|CONSTRAINT|PRIMARY KEY)\b', line, re.IGNORECASE):
                continue
            col_match = re.match(r'^(\w+)\s+(INTEGER|TEXT|REAL|BLOB|BOOLEAN)', line, re.IGNORECASE)
            if col_match:
                cols.append(col_match.group(1))
        tables[tname] = cols
    return tables


# ─────────────────────────────────────────────
# 2. 실제 DB 스키마
# ─────────────────────────────────────────────

def parse_db_schema(db_path: str) -> dict[str, list[str]] | None:
    """SQLite DB에서 테이블명 → 컬럼명 리스트."""
    p = Path(db_path)
    if not p.exists():
        return None
    conn = sqlite3.connect(str(p))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = {}
    for (tname,) in cursor.fetchall():
        cursor.execute(f"PRAGMA table_info({tname})")
        tables[tname] = [row[1] for row in cursor.fetchall()]
    conn.close()
    return tables


# ─────────────────────────────────────────────
# 3. 설계문서 카테고리 파싱
# ─────────────────────────────────────────────

def parse_arch_categories() -> dict[str, str]:
    """architecture.md에서 카테고리 목록 추출."""
    path = ROOT / "v0.3" / "data" / "architecture.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    cats = {}
    # "카테고리": "설명" 또는 | `카테고리` | 설명 | 패턴
    for m in re.finditer(r'["|`](\w+)["|`]\s*[:│|]\s*["|]?([^"|,\n]+)', text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key in METRIC_CATEGORIES or key.startswith("rp_"):
            cats[key] = val
    return cats


# ─────────────────────────────────────────────
# 4. 검증 로직
# ─────────────────────────────────────────────

def check_all(db_path: str | None = None) -> list[tuple[str, str]]:
    """전체 검증. 반환: [(severity, message), ...]"""
    results = []
    ddl = parse_ddl_tables()

    # ── Check 1: SSOT activity_summary ↔ DDL ──
    registry_as = {md.name for md in get_by_storage("activity_summary")}
    ddl_as = set(ddl.get("activity_summaries", []))
    mgmt = {"id", "source", "source_id", "matched_group_id", "created_at", "updated_at"}
    ddl_data = ddl_as - mgmt

    only_ssot = registry_as - ddl_data
    only_ddl = ddl_data - registry_as
    if only_ssot:
        results.append(("🔴", f"activity_summaries: SSOT에만 — {', '.join(sorted(only_ssot))}"))
    if only_ddl:
        results.append(("🔴", f"activity_summaries: DDL에만 (→ metric_store로 이전 필요) — {', '.join(sorted(only_ddl))}"))

    # ── Check 2: SSOT wellness ↔ DDL ──
    registry_wl = {md.name for md in get_by_storage("wellness")}
    ddl_wl = set(ddl.get("daily_wellness", [])) - {"id", "date", "created_at", "updated_at"}
    only_ssot_wl = registry_wl - ddl_wl
    only_ddl_wl = ddl_wl - registry_wl
    if only_ssot_wl:
        results.append(("🔴", f"daily_wellness: SSOT에만 — {', '.join(sorted(only_ssot_wl))}"))
    if only_ddl_wl:
        results.append(("🔴", f"daily_wellness: DDL에만 — {', '.join(sorted(only_ddl_wl))}"))

    # ── Check 3: daily_fitness 삭제 확인 ──
    if "daily_fitness" in ddl:
        results.append(("🔴", "daily_fitness: DDL에 존재 — 삭제 대상 (metric_store로 대체됨)"))

    # ── Check 4: 카테고리 정합성 ──
    cats_used = set(md.category for md in METRIC_REGISTRY.values())
    cats_defined = set(METRIC_CATEGORIES.keys()) - {"_unmapped"}
    if cats_used - cats_defined:
        results.append(("🔴", f"카테고리 미정의: {', '.join(sorted(cats_used - cats_defined))}"))
    unused = cats_defined - cats_used
    if unused:
        results.append(("🟡", f"카테고리 미사용: {', '.join(sorted(unused))}"))

    # ── Check 5: MetricDef 필드 검증 ──
    valid_storages = {"activity_summary", "wellness", "metric"}
    valid_scopes = {"activity", "daily", "weekly", "athlete"}
    for name, md in METRIC_REGISTRY.items():
        if md.storage not in valid_storages:
            results.append(("🔴", f"MetricDef '{name}': 잘못된 storage='{md.storage}'"))
        if md.scope not in valid_scopes:
            results.append(("🔴", f"MetricDef '{name}': 잘못된 scope='{md.scope}'"))
        if md.category not in METRIC_CATEGORIES:
            results.append(("🔴", f"MetricDef '{name}': 미정의 category='{md.category}'"))

    # ── Check 6: 중복 이름 ──
    from collections import Counter
    names = [md.name for md in METRIC_REGISTRY.values()]
    dupes = {k: v for k, v in Counter(names).items() if v > 1}
    for name, count in dupes.items():
        results.append(("🔴", f"MetricDef 중복: '{name}' × {count}"))

    # ── Check 7: alias 충돌 ──
    alias_map = {}
    for md in METRIC_REGISTRY.values():
        for src, raw in md.aliases.items():
            key = f"{src}::{raw}"
            if key in alias_map and alias_map[key] != md.name:
                results.append(("🔴", f"alias 충돌: {key} → '{alias_map[key]}' vs '{md.name}'"))
            alias_map[key] = md.name

    # ── Check 8: scope 일관성 ──
    for md in METRIC_REGISTRY.values():
        if md.storage == "wellness" and md.scope != "daily":
            results.append(("🟠", f"wellness '{md.name}': scope이 '{md.scope}'이나 'daily'여야 함"))
        if md.storage == "activity_summary" and md.scope != "activity":
            results.append(("🟠", f"activity_summary '{md.name}': scope이 '{md.scope}'이나 'activity'여야 함"))

    # ── Check 9: 실제 DB 검증 (선택) ──
    if db_path:
        db_schema = parse_db_schema(db_path)
        if db_schema:
            for tname in ["activity_summaries", "daily_wellness", "metric_store"]:
                ddl_cols = set(ddl.get(tname, []))
                db_cols = set(db_schema.get(tname, []))
                if ddl_cols and db_cols:
                    only_ddl_t = ddl_cols - db_cols
                    only_db_t = db_cols - ddl_cols
                    if only_ddl_t:
                        results.append(("🔴", f"DB '{tname}': DDL에만 — {', '.join(sorted(only_ddl_t))}"))
                    if only_db_t:
                        results.append(("🔴", f"DB '{tname}': DB에만 — {', '.join(sorted(only_db_t))}"))
                elif not db_cols and ddl_cols:
                    results.append(("🟠", f"DB '{tname}': DDL에 있으나 DB에 없음"))
        else:
            results.append(("🟡", f"DB 파일 없음: {db_path}"))

    # ── Check 10: Extractor _metric() category 값 검증 ──
    # _metric() 호출에서 category= kwarg가 16-domain 카테고리 내인지 확인.
    extractor_dir = ROOT / "src" / "sync" / "extractors"
    valid_cats = set(METRIC_CATEGORIES.keys())  # 16개 + _unmapped
    for ext_file in sorted(extractor_dir.glob("*_extractor.py")):
        text = ext_file.read_text(encoding="utf-8")
        for m in re.finditer(r'category=["\'](\w+)["\']', text):
            cat = m.group(1)
            if cat not in valid_cats:
                line_num = text[:m.start()].count('\n') + 1
                results.append(("🔴", f"Extractor 구버전 category — {ext_file.name}:{line_num} — '{cat}'"))

    # ── Check 11: Extractor _metric() 미등록 메트릭 이름 검출 ──
    # _metric("name", ...) 첫 인자가 METRIC_REGISTRY에 없고 어떤 alias 값에도 없으면 미등록.
    # 미등록 메트릭은 _unmapped category로 저장되어 검색/집계 불가.
    registered_names = set(METRIC_REGISTRY.keys())
    alias_values: set[str] = set()
    for md in METRIC_REGISTRY.values():
        for raw in md.aliases.values():
            alias_values.add(raw)
    for ext_file in sorted(extractor_dir.glob("*_extractor.py")):
        text = ext_file.read_text(encoding="utf-8")
        for m in re.finditer(r'self\._metric\(["\'](\w+)["\']\s*,', text):
            name = m.group(1)
            if name not in registered_names and name not in alias_values:
                line_num = text[:m.start()].count('\n') + 1
                results.append(("🔴", f"Extractor 미등록 메트릭 — {ext_file.name}:{line_num} — '{name}'"))

    # ── Check 12: Extractor _metric() 폐기 예정 메트릭 이름 검출 ──
    # 제거가 확정된 메트릭이 extractor에 다시 추가되지 않도록 방어.
    deprecated: dict[str, str] = {
        # 예시: "metric_name": "제거 사유"
    }
    for ext_file in sorted(extractor_dir.glob("*_extractor.py")):
        text = ext_file.read_text(encoding="utf-8")
        for m in re.finditer(r'self\._metric\(["\'](\w+)["\']\s*,', text):
            name = m.group(1)
            if name in deprecated:
                line_num = text[:m.start()].count('\n') + 1
                results.append(("🟠", f"Extractor 폐기 예정 메트릭 — {ext_file.name}:{line_num} — '{name}' ({deprecated[name]})"))

    # ── Check 13: Garmin wellness entity_type 이름 일관성 ──
    # garmin_wellness_sync.py의 WELLNESS_ENDPOINTS 키와
    # reprocess.py의 wellness_types가 동일한 wellness_* 이름을 사용하는지 확인.
    # 설계 spec: wellness_sleep, wellness_hrv, wellness_body_battery,
    #            wellness_stress, wellness_user_summary, wellness_training_readiness
    REQUIRED_WELLNESS_TYPES = {
        "wellness_sleep", "wellness_hrv", "wellness_body_battery",
        "wellness_stress", "wellness_user_summary", "wellness_training_readiness",
    }
    OLD_WELLNESS_TYPES = {"sleep_day", "hrv_day", "body_battery_day",
                          "stress_day", "user_summary_day"}

    sync_dir = ROOT / "src" / "sync"
    gws_path = sync_dir / "garmin_wellness_sync.py"
    rp_path = sync_dir / "reprocess.py"

    if gws_path.exists():
        text = gws_path.read_text(encoding="utf-8")
        missing = [t for t in REQUIRED_WELLNESS_TYPES if t not in text]
        old_found = [t for t in OLD_WELLNESS_TYPES if f'"{t}"' in text or f"'{t}'" in text]
        if missing:
            results.append(("🔴", f"garmin_wellness_sync.py: 설계 entity_type 누락 — {', '.join(sorted(missing))}"))
        if old_found:
            results.append(("🔴", f"garmin_wellness_sync.py: 구버전 entity_type 사용 — {', '.join(old_found)}"))
        if not missing and not old_found:
            pass  # OK — 출력은 check_docs.py에서 담당

    if rp_path.exists():
        text = rp_path.read_text(encoding="utf-8")
        old_found = [t for t in OLD_WELLNESS_TYPES if f'"{t}"' in text or f"'{t}'" in text]
        if old_found:
            results.append(("🔴", f"reprocess.py: 구버전 wellness entity_type 사용 — {', '.join(old_found)}"))

    # ── Check 14: Calculator category 속성 16-domain 준수 ──
    # 구버전 rp_* 카테고리 재유입 방지.
    try:
        from src.metrics.engine import ALL_CALCULATORS as _all_calcs
        valid_calc_cats = set(METRIC_CATEGORIES.keys()) - {"_unmapped"}
        for _calc in _all_calcs:
            _cat = getattr(_calc, "category", None)
            _name = getattr(_calc, "name", "?")
            if _cat and _cat not in valid_calc_cats:
                results.append(("🔴", f"Calculator '{_name}': 16-domain 외 category='{_cat}'"))
        _bad = [getattr(c, "name", "?") for c in _all_calcs
                if getattr(c, "category", None) not in valid_calc_cats]
        if not _bad:
            results.append(("✅", f"Calculator category 전체 16-domain 준수 ({len(_all_calcs)}개)"))
    except ImportError as e:
        results.append(("🟡", f"ALL_CALCULATORS import 실패 — Check 14 건너뜀: {e}"))

    # ── Check 15: Calculator produces ↔ METRIC_REGISTRY 등록 일치 ──
    # Calculator가 생성하는 메트릭이 METRIC_REGISTRY에 등록되어 있어야 함.
    try:
        from src.metrics.engine import ALL_CALCULATORS as _all_calcs2
        _registered = set(METRIC_REGISTRY.keys())
        _missing_produces = []
        for _calc in _all_calcs2:
            _cname = getattr(_calc, "name", "?")
            _produces = getattr(_calc, "produces", None) or [_cname]
            for _metric in _produces:
                if isinstance(_metric, str) and _metric not in _registered:
                    _missing_produces.append(f"'{_cname}' → '{_metric}'")
        if _missing_produces:
            for mp in _missing_produces:
                results.append(("🔴", f"Calculator produces 미등록: {mp}"))
        else:
            results.append(("✅", "Calculator produces 전체 METRIC_REGISTRY 등록 확인"))
    except ImportError as e:
        results.append(("🟡", f"ALL_CALCULATORS import 실패 — Check 15 건너뜀: {e}"))

    # ── Check 16: DataValidator 구조 일관성 ──
    # _check_* 메서드가 설계대로 12개인지, CheckResult 필드가 올바른지 검증.
    validator_path = ROOT / "src" / "validation" / "validator.py"
    if not validator_path.exists():
        results.append(("🔴", "src/validation/validator.py 없음 — Phase 6 미구현"))
    else:
        import re as _re
        v_text = validator_path.read_text(encoding="utf-8")

        # _check_* 메서드 수
        check_methods = _re.findall(r"def (_check_\w+)", v_text)
        if len(check_methods) != 12:
            results.append(("🔴", f"DataValidator: _check_* 메서드 수 {len(check_methods)}개 (설계: 12개) — {check_methods}"))
        else:
            results.append(("✅", f"DataValidator: _check_* 메서드 12개 확인"))

        # CheckResult 필드 — name, status, expected, actual, message
        for field in ("name", "status", "expected", "actual", "message"):
            if field not in v_text:
                results.append(("🔴", f"CheckResult: '{field}' 필드 없음"))

        # run_all() 반환 타입 힌트 — list[CheckResult]
        if "def run_all" not in v_text:
            results.append(("🔴", "DataValidator.run_all() 없음"))

        # PASS/WARN/FAIL 상태 문자열 모두 사용 중인지
        for status in ("PASS", "WARN", "FAIL"):
            if f'"{status}"' not in v_text and f"'{status}'" not in v_text:
                results.append(("🟠", f"DataValidator: '{status}' 상태 미사용"))

        # GarminBulkLoader와의 연계 — source_payloads / metric_store 쿼리
        for table in ("source_payloads", "metric_store", "activity_summaries"):
            if table not in v_text:
                results.append(("🟠", f"DataValidator: '{table}' 테이블 미참조 (체크 누락 가능성)"))

    return results


# ─────────────────────────────────────────────
# 5. 출력
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RunPulse 데이터 정합성 검증")
    parser.add_argument("--db", default=None, help="SQLite DB 경로 (선택)")
    args = parser.parse_args()

    results = check_all(args.db)

    red = [r for r in results if r[0] == "🔴"]
    orange = [r for r in results if r[0] == "🟠"]
    yellow = [r for r in results if r[0] == "🟡"]

    print(f"\n{'='*60}")
    print(f"  RunPulse 데이터 정합성 검증 결과")
    print(f"{'='*60}")
    print(f"  MetricDefs: {len(METRIC_REGISTRY)}")
    print(f"  Categories: {len(METRIC_CATEGORIES) - 1}")
    print(f"  검증 항목: 16")
    print(f"{'='*60}")
    print(f"  🔴 오류:  {len(red)}")
    print(f"  🟠 경고:  {len(orange)}")
    print(f"  🟡 참고:  {len(yellow)}")
    print(f"{'='*60}\n")

    for sev, msg in results:
        if sev == "✅":
            continue  # OK 항목은 요약에서 생략
        print(f"  {sev} {msg}")

    if not results:
        print("  ✅ 모든 검증 통과!")

    print()

    if red:
        sys.exit(2)
    elif orange or yellow:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
