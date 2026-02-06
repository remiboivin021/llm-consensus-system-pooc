import ast
import types

import pytest

import src.core.scoring.engine as eng


def test_extract_code_prefers_file_and_decodes():
    payload = r'{"files": [{"filename": "main.py", "code": "def foo():\\n    return 1"}]}'
    code = eng._extract_code(payload)
    assert "return 1" in code


def test_extract_code_falls_back_to_markdown():
    markdown = """Here is code

```python
def add(a, b):
    return a + b
```
"""
    code = eng._extract_code(markdown)
    assert "def add" in code


def test_extract_code_returns_raw_when_no_signal():
    raw = "plain text without code"
    assert eng._extract_code(raw) == raw


def test_performance_score_bounds():
    assert eng._performance_score(None) == 0.5
    assert eng._performance_score(10, max_latency=20) == pytest.approx(0.5)
    assert eng._performance_score(10_000) == 0.0


def test_complexity_score_handles_missing_dependencies(monkeypatch):
    monkeypatch.setattr(eng, "cc_visit", None)
    monkeypatch.setattr(eng, "mi_visit", None)
    monkeypatch.setattr(eng, "h_visit", None)
    score, meta = eng._complexity_score("def x():\n    return 1")
    assert score == 0.5
    assert meta == {}


def test_complexity_score_with_stubbed_metrics(monkeypatch):
    class CC(types.SimpleNamespace):
        pass

    monkeypatch.setattr(eng, "cc_visit", lambda content: [types.SimpleNamespace(complexity=8)])
    monkeypatch.setattr(eng, "mi_visit", lambda content, multi=True: 70)

    class Hal(types.SimpleNamespace):
        pass

    monkeypatch.setattr(
        eng,
        "h_visit",
        lambda content: [types.SimpleNamespace(difficulty=20.0, effort=5000.0)],
    )
    score, meta = eng._complexity_score("def x(a):\n    return a * 2\n")
    assert 0.6 < score <= 1.0
    assert meta["radon_mi"] == 70
    assert meta["radon_complexity"] == 8
    assert meta["halstead_difficulty"] == 20.0
    assert meta["halstead_effort"] == 5000.0


def test_tests_score_small_file_without_tests():
    tree = ast.parse("x = 1\n")
    score, meta = eng._tests_score(tree, lines_count=2)
    assert score == pytest.approx(0.7)
    assert meta["assertions"] == 0


def test_tests_score_with_asserts_and_imports():
    code = """
import pytest

def test_example():
    assert 1 == 1
"""
    tree = ast.parse(code)
    score, meta = eng._tests_score(tree, lines_count=len(code.splitlines()))
    assert score == pytest.approx(0.8)
    assert meta["test_funcs"] == 1
    assert meta["test_imports"] is True


def test_style_score_handles_missing_checker(monkeypatch):
    monkeypatch.setattr(eng, "Checker", None)
    score, meta = eng._style_score("def x():\n    pass\n")
    assert score == 0.5
    assert meta["critical"] == 0


def test_style_score_with_stub_checker(monkeypatch):
    class FakeChecker:
        def __init__(self, lines):
            self.lines = lines

        def check_all(self):
            return 4

    monkeypatch.setattr(eng, "Checker", FakeChecker)
    score, meta = eng._style_score("def y():\n    return 1\n")
    assert score == pytest.approx(0.6)
    assert meta["critical"] == 4


def test_documentation_score_basics(monkeypatch):
    monkeypatch.setattr(eng, "pydocstyle", None)
    content = "def f():\n    pass\n"
    tree = ast.parse(content)
    score, meta = eng._documentation_score(tree, content)
    assert score == 0.0
    assert meta["total"] == 1


def test_documentation_score_with_docstring_and_errors(monkeypatch):
    class DummyPydoc:
        @staticmethod
        def check(files, filename=None):
            # simulate one style error
            return [object()]

    monkeypatch.setattr(eng, "pydocstyle", DummyPydoc)
    content = 'def g():\n    """doc"""\n    return 1\n'
    tree = ast.parse(content)
    score, meta = eng._documentation_score(tree, content)
    assert score < 1.0
    assert meta["documented"] == 1
    assert meta["pydocstyle_errors"] == 1


def test_dead_code_score_missing_dependency(monkeypatch):
    monkeypatch.setattr(eng, "Vulture", None)
    score, meta = eng._dead_code_score("def x():\n    return 1\n")
    assert score == 0.5
    assert meta["unused"] == 0


def test_dead_code_score_with_unused_symbols(monkeypatch):
    class FakeItem:
        def __init__(self, typ):
            self.typ = typ

    class FakeVulture:
        def scan(self, content, filename=None):
            return None

        def get_unused_code(self):
            return [FakeItem("unused function"), FakeItem("unused variable")]

    monkeypatch.setattr(eng, "Vulture", FakeVulture)
    score, meta = eng._dead_code_score("def unused():\n    return 1\n")
    assert score == pytest.approx(0.8)
    assert meta["unused"] == 2


def test_security_score_with_eval_and_missing_bandit(monkeypatch):
    monkeypatch.setattr(eng, "manager", None)
    monkeypatch.setattr(eng, "bandit_config", None)
    score, meta = eng._security_score("eval('x')")
    assert score == 0.0
    assert meta["security_issues"] == 0


    def test_security_score_with_bandit_findings(monkeypatch):
        class FakeIssue:
            def __init__(self, severity):
                self.severity = severity

        class FakeBanditManager:
            def __init__(self, cfg, profile):
                self.lines = {}

            def discover_files(self, files):
                self.files_list = files

            def run_tests(self):
                return None

            def get_issue_list(self, sev_level="LOW", conf_level="LOW"):
                return [FakeIssue("HIGH"), FakeIssue("LOW")]

        class FakeManagerModule:
            BanditManager = FakeBanditManager

        class FakeBanditConfig:
            class BanditConfig:
                def __init__(self):
                    pass

        monkeypatch.setattr(eng, "manager", FakeManagerModule)
        monkeypatch.setattr(eng, "bandit_config", FakeBanditConfig)

        score, meta = eng._security_score("def safe():\n    return 1\n")
        assert score == pytest.approx(0.68)
        assert meta["security_issues"] == 2


def test_compute_statistics_edge_cases():
    stats = eng._compute_statistics([], 0)
    assert stats.mean == stats.min == stats.max == stats.stddev == 0.0
    assert stats.count == 0

    stats = eng._compute_statistics([0.2, 0.8], 2)
    assert stats.mean == pytest.approx(0.5)
    assert stats.min == 0.2
    assert stats.max == 0.8
    assert stats.stddev > 0
