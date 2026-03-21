from tests.helpers.fixture_loader import FIXTURES_ROOT, fixture_path, read_text_fixture


def test_fixture_root_exists():
    assert FIXTURES_ROOT.exists()


def test_fixture_path_resolves_readme():
    path = fixture_path("README.md")
    assert path.exists()
    assert path.name == "README.md"


def test_read_text_fixture_reads_readme():
    content = read_text_fixture("README.md")
    assert "테스트 fixture 안내" in content
    assert "디렉토리 구조" in content
