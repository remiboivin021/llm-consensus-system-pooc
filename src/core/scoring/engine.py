from __future__ import annotations

import ast
import json
import math
import re
from typing import List, Sequence, Tuple

try:
    from radon.complexity import cc_visit
    from radon.metrics import h_visit, mi_visit
except Exception:  # pragma: no cover - optional import
    cc_visit = mi_visit = h_visit = None  # type: ignore

try:
    from pycodestyle import Checker
except Exception:  # pragma: no cover
    Checker = None  # type: ignore

try:
    import pydocstyle
except Exception:  # pragma: no cover
    pydocstyle = None  # type: ignore

try:
    from vulture import Vulture
except Exception:  # pragma: no cover
    Vulture = None  # type: ignore

try:
    from bandit.core import manager, config as bandit_config
except Exception:  # pragma: no cover
    manager = bandit_config = None  # type: ignore

from src.contracts.response import ModelResponse, ScoreDetail, ScoreStats

WEIGHTS = {
    "performance": 0.10,
    "complexity": 0.20,
    "tests": 0.15,
    "style": 0.10,
    "documentation": 0.15,
    "dead_code": 0.10,
    "security": 0.20,
}


def _decode_escapes(value: str) -> str:
    try:
        return value.encode("utf-8").decode("unicode_escape")
    except Exception:
        return value


def _extract_code(content: str) -> str:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if isinstance(data.get("files"), list) and data["files"]:
                first = data["files"][0]
                if isinstance(first, dict):
                    code_value = first.get("code")
                    if isinstance(code_value, str) and code_value.strip():
                        return _decode_escapes(code_value)
            code_value = data.get("code")
            if isinstance(code_value, str) and code_value.strip():
                return _decode_escapes(code_value)
    except Exception:
        pass

    block = re.search(r"```(?:python)?\s*([\s\S]*?)```", content, re.MULTILINE)
    if block:
        extracted = block.group(1).strip()
        if extracted:
            return extracted

    return content


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _performance_score(latency_ms: int | None, max_latency: int = 5000) -> float:
    if latency_ms is None:
        return 0.5
    score = 1.0 - (latency_ms / max_latency)
    return _clamp(score)


def _cyclomatic_score(avg_complexity: float) -> float:
    if avg_complexity <= 5:
        return 1.0
    if avg_complexity <= 10:
        return 0.8
    if avg_complexity <= 20:
        return 0.5
    if avg_complexity <= 30:
        return 0.3
    return 0.0


def _mi_score(mi: float) -> float:
    if mi > 85:
        return 1.0
    if mi > 65:
        return 0.7
    if mi > 20:
        return 0.4
    return 0.0


def _halstead_score(difficulty: float, effort: float) -> float:
    diff_score = _clamp(1.0 - min(difficulty / 50.0, 1.0))
    effort_score = _clamp(1.0 - min(effort / 10000.0, 1.0))
    return (diff_score + effort_score) / 2.0


def _complexity_score(content: str) -> tuple[float, dict]:
    if not cc_visit or not mi_visit or not h_visit:
        return 0.5, {}

    try:
        cc_results = cc_visit(content) or []
        avg_cc = sum(r.complexity for r in cc_results) / len(cc_results) if cc_results else 0.0
        mi = mi_visit(content, multi=True)
        halstead = h_visit(content) or []
        halstead_avg = halstead[0] if halstead else None
        halstead_score = (
            _halstead_score(halstead_avg.difficulty, halstead_avg.effort) if halstead_avg else 1.0
        )

        complexity_score = (
            _cyclomatic_score(avg_cc) * 0.4
            + _mi_score(mi) * 0.4
            + halstead_score * 0.2
        )
        meta = {
            "radon_mi": mi,
            "radon_complexity": avg_cc,
            "halstead_difficulty": getattr(halstead_avg, "difficulty", None),
            "halstead_effort": getattr(halstead_avg, "effort", None),
        }
        return _clamp(complexity_score), meta
    except Exception:
        return 0.5, {}


def _tests_score(tree: ast.AST, lines_count: int) -> tuple[float, dict]:
    assertions = 0
    test_funcs = 0
    test_imports = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            assertions += 1
        if isinstance(node, ast.FunctionDef):
            has_test_decorator = any(
                isinstance(dec, ast.Name) and dec.id.startswith("pytest")
                or (isinstance(dec, ast.Attribute) and dec.attr.startswith("mark"))
                for dec in node.decorator_list
            )
            if node.name.startswith("test_") or has_test_decorator:
                test_funcs += 1
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if any(name.split(".")[0] in {"unittest", "pytest", "nose", "hypothesis"} for name in names):
                test_imports = True

    if test_funcs == 0 and assertions == 0:
        return (0.7 if lines_count < 10 else 0.3), {
            "assertions": assertions,
            "test_funcs": test_funcs,
            "test_imports": test_imports,
            "coverage_estimate": 0.0,
        }

    expected_assertions = max(test_funcs * 3, 1)
    coverage_estimate = min(assertions / expected_assertions, 1.0)
    score = (
        (0.3 if test_funcs > 0 else 0.0)
        + (0.2 if assertions > 0 else 0.0)
        + (0.2 if test_imports else 0.0)
        + (0.3 * coverage_estimate)
    )
    return _clamp(score), {
        "assertions": assertions,
        "test_funcs": test_funcs,
        "test_imports": test_imports,
        "coverage_estimate": coverage_estimate,
    }


def _style_score(content: str) -> tuple[float, dict]:
    if not Checker:
        return 0.5, {"critical": 0, "minor": 0}

    try:
        checker = Checker(lines=content.splitlines())
        violations = checker.check_all()
    except Exception:
        violations = 0

    critical = violations
    minor = 0
    total_lines = max(len(content.splitlines()), 1)
    penalty = (critical * 0.1) + (minor * 0.02)
    score = max(0.0, 1.0 - (penalty / max(total_lines / 10, 1)))
    return _clamp(score), {"critical": critical, "minor": minor}


def _documentation_score(tree: ast.AST, content: str) -> tuple[float, dict]:
    public_funcs = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    public_classes = [
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]
    documented = sum(1 for node in public_funcs + public_classes if ast.get_docstring(node))
    total = len(public_funcs + public_classes)
    coverage = documented / max(total, 1)

    pydoc_errors = 0
    if pydocstyle:
        try:
            for err in pydocstyle.check((content,), filename="<string>"):  # type: ignore
                pydoc_errors += 1
        except Exception:
            pydoc_errors = 0

    quality_penalty = pydoc_errors * 0.05
    doc_score = max(0.0, coverage - quality_penalty)
    return _clamp(doc_score), {
        "documented": documented,
        "total": total,
        "pydocstyle_errors": pydoc_errors,
    }


def _dead_code_score(content: str) -> tuple[float, dict]:
    if not Vulture:
        return 0.5, {"unused": 0}
    try:
        v = Vulture()
        v.scan(content, filename="<string>")
        unused_items = v.get_unused_code()
        penalty = 0.0
        for item in unused_items:
            typ = getattr(item, "typ", "")
            if typ == "unused function":
                penalty += 0.15
            elif typ == "unused class":
                penalty += 0.20
            elif typ == "unused variable":
                penalty += 0.05
            elif typ == "unused import":
                penalty += 0.03
            else:
                penalty += 0.01
        return max(0.0, 1.0 - penalty), {"unused": len(unused_items)}
    except Exception:
        return 0.5, {"unused": 0}


def _security_score(content: str) -> tuple[float, dict]:
    issues = []
    if manager and bandit_config:
        try:
            cfg = bandit_config.BanditConfig()
            mgr = manager.BanditManager(cfg, "file")
            mgr.discover_files(["<string>"])
            mgr.parse_results = True
            mgr.files_list = ["<string>"]
            mgr.lines = {"<string>": content.splitlines()}
            mgr.run_tests()
            issues = mgr.get_issue_list(sev_level="LOW", conf_level="LOW")  # type: ignore
        except Exception:
            issues = []

    security_score = 1.0
    if "eval(" in content or "exec(" in content:
        security_score = 0.0
    else:
        for issue in issues:
            sev = getattr(issue, "severity", "").upper()
            if sev == "HIGH":
                security_score -= 0.3
            elif sev == "MEDIUM":
                security_score -= 0.1
            elif sev == "LOW":
                security_score -= 0.02
        security_score = max(0.0, security_score)
    return security_score, {"security_issues": len(issues)}


def _compute_statistics(values: Sequence[float], count: int) -> ScoreStats:
    if count == 0 or not values:
        return ScoreStats(mean=0.0, min=0.0, max=0.0, stddev=0.0, count=count)

    mean = sum(values) / count
    min_value = min(values)
    max_value = max(values)
    variance = sum((value - mean) ** 2 for value in values) / count
    stddev = math.sqrt(variance)
    return ScoreStats(
        mean=_clamp(mean),
        min=_clamp(min_value),
        max=_clamp(max_value),
        stddev=stddev,
        count=count,
    )


def compute_scores(responses: List[ModelResponse]) -> Tuple[List[ScoreDetail], ScoreStats]:
    details: list[ScoreDetail] = []
    scored_values: list[float] = []

    for response in responses:
        content = (response.content or "").strip()
        metadata: dict = {}

        if response.error is not None or not content:
            detail = ScoreDetail(
                model=response.model,
                performance=_performance_score(response.latency_ms),
                complexity=0.0,
                tests=0.0,
                style=0.0,
                documentation=0.0,
                dead_code=0.0,
                security=0.0,
                score=0.0,
                error=True,
                metadata=metadata,
            )
            details.append(detail)
            continue

        code = _extract_code(content)

        try:
            tree = ast.parse(code)
        except SyntaxError:
            detail = ScoreDetail(
                model=response.model,
                performance=_performance_score(response.latency_ms),
                complexity=0.0,
                tests=0.0,
                style=0.0,
                documentation=0.0,
                dead_code=0.0,
                security=0.0,
                score=0.0,
                error=True,
                metadata=metadata,
            )
            details.append(detail)
            continue

        performance = _performance_score(response.latency_ms)
        complexity, complexity_meta = _complexity_score(code)
        tests_score, tests_meta = _tests_score(tree, len(code.splitlines()))
        style_score, style_meta = _style_score(code)
        doc_score, doc_meta = _documentation_score(tree, code)
        dead_code_score, dead_meta = _dead_code_score(code)
        security_score, sec_meta = _security_score(code)

        scores = {
            "performance": performance,
            "complexity": complexity,
            "tests": tests_score,
            "style": style_score,
            "documentation": doc_score,
            "dead_code": dead_code_score,
            "security": security_score,
        }
        overall = _clamp(
            sum(scores[metric] * weight for metric, weight in WEIGHTS.items())
        )

        metadata.update(
            complexity_meta
            | tests_meta
            | style_meta
            | doc_meta
            | dead_meta
            | sec_meta
        )

        detail = ScoreDetail(
            model=response.model,
            performance=performance,
            complexity=complexity,
            tests=tests_score,
            style=style_score,
            documentation=doc_score,
            dead_code=dead_code_score,
            security=security_score,
            score=overall,
            error=False,
            metadata=metadata or None,
        )
        details.append(detail)
        scored_values.append(overall)

    stats = _compute_statistics(scored_values, len(scored_values))
    return details, stats
