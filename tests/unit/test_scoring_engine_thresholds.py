import types

import pytest

import src.core.scoring.engine as eng


@pytest.mark.parametrize(
    "value,expected",
    [(4, 1.0), (8, 0.8), (15, 0.5), (25, 0.3), (40, 0.0)],
)
def test_cyclomatic_score_branches(value, expected):
    assert eng._cyclomatic_score(value) == expected


@pytest.mark.parametrize(
    "mi,expected",
    [(90, 1.0), (75, 0.7), (40, 0.4), (5, 0.0)],
)
def test_mi_score_branches(mi, expected):
    assert eng._mi_score(mi) == expected


def test_halstead_score_bounds():
    assert eng._halstead_score(0.0, 0.0) == 1.0
    assert eng._halstead_score(1000.0, 50000.0) < 0.2


def test_performance_score_negative_latency():
    assert eng._performance_score(-1, max_latency=10) == 1.0


def test_complexity_score_exception_fallback(monkeypatch):
    def raiser(content):
        raise RuntimeError("boom")

    monkeypatch.setattr(eng, "cc_visit", raiser)
    monkeypatch.setattr(eng, "mi_visit", raiser)
    monkeypatch.setattr(eng, "h_visit", raiser)
    score, meta = eng._complexity_score("def x():\n    return 1\n")
    assert score == 0.5
    assert meta == {}


def test_style_score_exception_path(monkeypatch):
    class Checker:
        def __init__(self, lines):
            pass

        def check_all(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(eng, "Checker", Checker)
    score, meta = eng._style_score("def x():\n    return 1\n")
    assert score >= 0.0
    assert meta["critical"] == 0


def test_documentation_score_pydocstyle_errors(monkeypatch):
    class DummyError: ...

    class DummyPydoc:
        @staticmethod
        def check(files, filename=None):
            return [DummyError(), DummyError()]

    monkeypatch.setattr(eng, "pydocstyle", DummyPydoc)
    content = "def f():\n    pass\n"
    tree = eng.ast.parse(content)
    score, meta = eng._documentation_score(tree, content)
    assert meta["pydocstyle_errors"] == 2
    assert score >= 0.0


def test_dead_code_score_exception_path(monkeypatch):
    class V:
        def scan(self, content, filename=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(eng, "Vulture", V)
    score, meta = eng._dead_code_score("def x():\n    return 1\n")
    assert score == 0.5
    assert meta["unused"] == 0


def test_security_score_bandit_exception(monkeypatch):
    class FakeManager:
        class BanditManager:
            def __init__(self, cfg, profile):
                raise RuntimeError("boom")

    class FakeConfig:
        class BanditConfig:
            def __init__(self):
                pass

    monkeypatch.setattr(eng, "manager", FakeManager)
    monkeypatch.setattr(eng, "bandit_config", FakeConfig)
    score, meta = eng._security_score("def ok():\n    return 1\n")
    assert score == 1.0  # no issues
    assert meta["security_issues"] == 0


def test_compute_statistics_single_value():
    stats = eng._compute_statistics([0.4], 1)
    assert stats.min == stats.max == stats.mean == 0.4
