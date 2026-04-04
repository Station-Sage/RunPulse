"""문서 동기화 검증 테스트.

calculator 추가/변경 시 metric_dictionary.md가 최신인지 자동 감지.
실패 시: python scripts/gen_metric_dictionary.py 실행 후 커밋.
"""
import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestMetricDictionarySync:
    """metric_dictionary.md가 코드와 동기화되었는지 검증."""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from src.metrics.engine import ALL_CALCULATORS
        from src.utils.metric_groups import SEMANTIC_GROUPS
        self.calculators = ALL_CALCULATORS
        self.groups = SEMANTIC_GROUPS
        self.dict_path = ROOT / "v0.3" / "data" / "metric_dictionary.md"

    def test_dictionary_exists(self):
        assert self.dict_path.exists(), (
            "metric_dictionary.md가 없습니다.\n"
            "실행: python scripts/gen_metric_dictionary.py"
        )

    def test_calculator_count_matches(self):
        if not self.dict_path.exists():
            pytest.skip("metric_dictionary.md 없음")
        text = self.dict_path.read_text(encoding="utf-8")
        match = re.search(r"(\d+) calculators", text)
        assert match, "metric_dictionary.md에서 calculator 수를 찾을 수 없음"
        doc_count = int(match.group(1))
        code_count = len(self.calculators)
        assert doc_count == code_count, (
            f"Calculator 수 불일치: 문서={doc_count}, 코드={code_count}\n"
            f"실행: python scripts/gen_metric_dictionary.py"
        )

    def test_group_count_matches(self):
        if not self.dict_path.exists():
            pytest.skip("metric_dictionary.md 없음")
        text = self.dict_path.read_text(encoding="utf-8")
        match = re.search(r"(\d+) semantic groups", text)
        assert match, "metric_dictionary.md에서 group 수를 찾을 수 없음"
        doc_count = int(match.group(1))
        code_count = len(self.groups)
        assert doc_count == code_count, (
            f"Semantic group 수 불일치: 문서={doc_count}, 코드={code_count}\n"
            f"실행: python scripts/gen_metric_dictionary.py"
        )

    def test_all_calculators_documented(self):
        if not self.dict_path.exists():
            pytest.skip("metric_dictionary.md 없음")
        text = self.dict_path.read_text(encoding="utf-8")
        missing = []
        for calc in self.calculators:
            # produces 중 하나라도 문서에 있으면 OK
            found = any(f"`{p}`" in text for p in calc.produces)
            if not found:
                missing.append(calc.name)
        assert not missing, (
            f"metric_dictionary.md에 누락된 calculator: {missing}\n"
            f"실행: python scripts/gen_metric_dictionary.py"
        )

    def test_all_groups_documented(self):
        if not self.dict_path.exists():
            pytest.skip("metric_dictionary.md 없음")
        text = self.dict_path.read_text(encoding="utf-8")
        missing = []
        for gname in self.groups:
            if f"`{gname}`" not in text:
                missing.append(gname)
        assert not missing, (
            f"metric_dictionary.md에 누락된 group: {missing}\n"
            f"실행: python scripts/gen_metric_dictionary.py"
        )

    def test_no_outdated_table_count(self):
        """v0.3/data/*.md에서 '13개 테이블' 같은 outdated 표현 검사."""
        data_dir = ROOT / "v0.3" / "data"
        if not data_dir.exists():
            pytest.skip("v0.3/data 없음")
        issues = []
        for md in data_dir.glob("*.md"):
            text = md.read_text(encoding="utf-8")
            for line_num, line in enumerate(text.splitlines(), 1):
                if "13개 테이블" in line:
                    issues.append(f"{md.name}:{line_num}")
        assert not issues, f"'13개 테이블' outdated 표현 발견: {issues}"
