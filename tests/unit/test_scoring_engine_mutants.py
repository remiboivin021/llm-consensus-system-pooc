import ast
import json
import types

import pytest

import src.core.scoring.engine as eng


def test_decode_escapes_handles_newlines():
    value = r"line1\\nline2"
    assert "line2" in eng._decode_escapes(value)


def test_decode_escapes_handles_bad_sequence():
    bad = "\\uZZZZ"
    assert eng._decode_escapes(bad) == bad


def test_extract_code_prefers_code_field():
    payload = json.dumps({"code": "print('hi')"})
    assert eng._extract_code(payload) == "print('hi')"


def test_extract_code_returns_raw_on_json_error():
    raw = "{not-json"
    assert eng._extract_code(raw) == raw


def test_extract_code_prefers_first_file_code():
    payload = json.dumps({"files": [{"filename": "a", "code": "CODE_A"}, {"filename": "b", "code": "CODE_B"}]})
    assert eng._extract_code(payload) == 'CODE_A'


def test_extract_code_returns_content_if_no_code_fields():
    content = 'plain text content'
    assert eng._extract_code(content) == content


def test_extract_code_with_empty_code_key():
    payload = json.dumps({"code": ""})
    assert eng._extract_code(payload) == payload  # falls back to original content


def test_performance_score_clamps_bounds():
    assert eng._performance_score(0, max_latency=1) == 1.0
    assert eng._performance_score(10_000, max_latency=100) == 0.0
    assert eng._performance_score(-10, max_latency=100) == 1.0


def test_cyclomatic_score_thresholds():
    assert eng._cyclomatic_score(5) == 1.0
    assert eng._cyclomatic_score(8) == 0.8
    assert eng._cyclomatic_score(15) == 0.5
    assert eng._cyclomatic_score(25) == 0.3
    assert eng._cyclomatic_score(40) == 0.0


def test_mi_score_thresholds():
    assert eng._mi_score(90) == 1.0
    assert eng._mi_score(70) == 0.7
    assert eng._mi_score(30) == 0.4
    assert eng._mi_score(10) == 0.0


def test_halstead_score_high_difficulty():
    low = eng._halstead_score(1.0, 100.0)
    high = eng._halstead_score(100.0, 20_000.0)
    assert low > high


def test_complexity_score_empty_halstead(monkeypatch):
    monkeypatch.setattr(eng, "cc_visit", lambda content: [types.SimpleNamespace(complexity=1)])
    monkeypatch.setattr(eng, "mi_visit", lambda content, multi=True: 90)
    monkeypatch.setattr(eng, "h_visit", lambda content: [])
    score, meta = eng._complexity_score("def x():\n    return 1\n")
    assert score > 0.5
    assert meta["halstead_difficulty"] is None


def test_tests_score_high_coverage():
    code = """
def test_example():
    assert 1 == 1
    assert 2 == 2
"""
    tree = ast.parse(code)
    score, meta = eng._tests_score(tree, lines_count=len(code.splitlines()))
    assert score <= 1.0
    assert meta["assertions"] >= 2
    assert meta["test_funcs"] == 1


def test_tests_score_no_tests_long_file():
    tree = ast.parse("x = 1\n" * 50)
    score, meta = eng._tests_score(tree, lines_count=50)
    assert score < 0.5
    assert meta["coverage_estimate"] == 0.0


def test_tests_score_more_assertions_than_expected():
    code = """
def test_many():
    assert 1
    assert 2
    assert 3
    assert 4
"""
    tree = ast.parse(code)
    score, meta = eng._tests_score(tree, lines_count=len(code.splitlines()))
    # coverage estimate should clamp to 1.0
    assert meta["coverage_estimate"] == 1.0


def test_style_score_zero_violations(monkeypatch):
    class FakeChecker:
        def __init__(self, lines):
            self.lines = lines

        def check_all(self):
            return 0

    monkeypatch.setattr(eng, "Checker", FakeChecker)
    score, meta = eng._style_score("def x():\n    return 1\n")
    assert score == 1.0
    assert meta["critical"] == 0


def test_documentation_score_with_docstrings(monkeypatch):
    monkeypatch.setattr(eng, "pydocstyle", None)
    code = 'def f():\n    """doc"""\n    return 1\n'
    tree = ast.parse(code)
    score, meta = eng._documentation_score(tree, code)
    assert score > 0.0
    assert meta["documented"] == 1


def test_dead_code_score_penalizes_unused_types(monkeypatch):
    class FakeItem:
        def __init__(self, typ):
            self.typ = typ

    class FakeVulture:
        def scan(self, content, filename=None):
            return None

        def get_unused_code(self):
            return [
                FakeItem("unused function"),
                FakeItem("unused class"),
                FakeItem("unused variable"),
                FakeItem("unused import"),
                FakeItem("other"),
            ]

    monkeypatch.setattr(eng, "Vulture", FakeVulture)
    score, meta = eng._dead_code_score("def unused():\n    return 1\n")
    assert score < 1.0
    assert meta["unused"] == 5


def test_security_score_exec_zero(monkeypatch):
    monkeypatch.setattr(eng, "manager", None)
    monkeypatch.setattr(eng, "bandit_config", None)
    score, meta = eng._security_score("exec('x')")
    assert score == 0.0
    assert meta["security_issues"] == 0


def test_security_score_with_bandit_issue(monkeypatch):
    class Issue:
        def __init__(self, severity):
            self.severity = severity

    class FakeManager:
        class BanditManager:
            def __init__(self, cfg, profile):
                pass

            def discover_files(self, files):
                return None

            def run_tests(self):
                return None

            def get_issue_list(self, sev_level="LOW", conf_level="LOW"):
                return [Issue("MEDIUM")]

    class FakeConfig:
        class BanditConfig:
            def __init__(self):
                pass

    monkeypatch.setattr(eng, "manager", FakeManager)
    monkeypatch.setattr(eng, "bandit_config", FakeConfig)
    score, meta = eng._security_score("def ok():\n    return 1\n")
    assert score < 1.0
    assert meta["security_issues"] == 1


def test_security_score_multiple_medium_low(monkeypatch):
    class Issue:
        def __init__(self, severity):
            self.severity = severity

    class FakeManager:
        class BanditManager:
            def __init__(self, cfg, profile):
                pass

            def discover_files(self, files):
                return None

            def run_tests(self):
                return None

            def get_issue_list(self, sev_level="LOW", conf_level="LOW"):
                return [Issue("LOW"), Issue("MEDIUM")]

    class FakeConfig:
        class BanditConfig:
            def __init__(self):
                pass

    monkeypatch.setattr(eng, "manager", FakeManager)
    monkeypatch.setattr(eng, "bandit_config", FakeConfig)
    score, meta = eng._security_score("def ok():\n    return 1\n")
    assert score < 1.0
    assert meta["security_issues"] == 2


def test_compute_statistics_mixed_values():
    stats = eng._compute_statistics([0.2, 0.8, 1.2], 3)
    assert stats.max == 1.0  # clamped
    assert stats.mean <= 1.0
    assert stats.stddev > 0


def test_compute_scores_handles_empty_and_syntax_error():
    responses = [
        # empty content
        types.SimpleNamespace(model="m1", content="", latency_ms=10, error=None),
        # invalid code
        types.SimpleNamespace(model="m2", content="def bad(:", latency_ms=5, error=None),
    ]
    scores, stats = eng.compute_scores(responses)
    assert scores[0].error is True
    assert scores[1].error is True
    assert stats.count == 0
