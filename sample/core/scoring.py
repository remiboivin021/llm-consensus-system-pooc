from __future__ import annotations

import ast
import math
import re
from typing import List, Sequence, Tuple

try:
    from radon.complexity import cc_visit
    from radon.metrics import h_visit, mi_visit
except Exception:  # pragma: no cover - optional import
    cc_visit = mi_visit = h_visit = None  # type: ignore

try:
    from pycodestyle import BaseReport, Checker
except Exception:  # pragma: no cover
    BaseReport = Checker = None  # type: ignore

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

from sample.contracts.response import ModelResponse, ScoreDetail, ScoreStats


WEIGHTS = {
    "performance": 0.10,
    "complexity": 0.20,
    "tests": 0.15,
    "style": 0.10,
    "documentation": 0.15,
    "dead_code": 0.10,
    "security": 0.20,
}

import json
import re
from typing import Optional

def _extract_code_from_json_response(content: str) -> str | None:
    """
    Extract Python code from JSON-formatted LLM response.
    
    Expected format:
    {
      "files": [
        {"filename": "main.py", "code": "import os\\n..."},
        {"filename": "test_main.py", "code": "import pytest\\n..."}
      ],
      "description": "..."
    }
    
    Returns:
        Concatenated Python code from all files, or None if parsing fails
    """
    
    # Try to extract JSON from response
    # Some models might still wrap it in markdown despite instructions
    json_str = content.strip()
    
    # Remove markdown code blocks if present
    if json_str.startswith('```'):
        # Extract content between ```json and ```
        match = re.search(r'```(?:json)?\s*\n(.*?)\n```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            # Try to find JSON object boundaries
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
    
    # Try to parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Content preview: {json_str[:200]}")
        return None
    
    # Validate structure
    if not isinstance(data, dict) or 'files' not in data:
        print(f"Invalid JSON structure. Expected 'files' key, got: {list(data.keys())}")
        return None
    
    files = data['files']
    if not isinstance(files, list):
        print(f"'files' should be a list, got: {type(files)}")
        return None
    
    # Extract and concatenate code from all files
    code_blocks = []
    
    for file_entry in files:
        if not isinstance(file_entry, dict):
            continue
            
        filename = file_entry.get('filename', 'unknown')
        code = file_entry.get('code', '')
        if isinstance(code, str):
            # JSON responses often contain escaped newlines/backslashes; decode them.
            try:
                code = bytes(code, "utf-8").decode("unicode_escape")
            except Exception:
                # Best effort; fall back to raw code
                pass
        
        if not code or not isinstance(code, str):
            continue
        
        # Skip non-Python files
        if not filename.endswith('.py'):
            continue
        
        # Validate it's actual Python code
        if not _is_valid_python_code(code):
            print(f"Skipping {filename}: not valid Python code")
            continue
        
        code_blocks.append(code)
    
    if not code_blocks:
        print("No valid Python code found in JSON response")
        return None
    
    # Join all code blocks with double newline
    return '\n\n'.join(code_blocks)


def _is_valid_python_code(code: str) -> bool:
    """Quick validation that code contains Python syntax"""
    if not code.strip():
        return False
    
    # Check for Python keywords
    python_keywords = [
        'def ', 'class ', 'import ', 'from ', 
        'if ', 'for ', 'while ', 'return ', 
        'try:', 'except', 'with ', 'async ', 'await '
    ]
    
    return any(keyword in code for keyword in python_keywords)


def _extract_all_python_code_blocks(content: str) -> str | None:
    """
    Main extraction function with fallback.
    
    Tries JSON format first, then falls back to markdown code blocks.
    """
    
    # STRATEGY 1: Try JSON format first
    result = _extract_code_from_json_response(content)
    if result:
        return result
    
    # STRATEGY 2: Fallback to markdown code blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        return None
    
    python_code_blocks = []
    
    for block in matches:
        cleaned = _clean_markdown_block(block)
        if _is_valid_python_code(cleaned):
            python_code_blocks.append(cleaned)
    
    if not python_code_blocks:
        return None
    
    return '\n\n'.join(python_code_blocks)


def _clean_markdown_block(block: str) -> str:
    """Clean up markdown code blocks (your existing logic)"""
    lines = block.strip().split('\n')
    clean_lines = []
    
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Skip markdown headers
        if stripped_line.startswith('#') or \
           (stripped_line.startswith('**') and stripped_line.endswith('**')):
            continue
        
        # Skip file path comments at the start
        if i < 3 and stripped_line.startswith('# ') and '/' in stripped_line:
            continue
        
        clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()

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
            # pydocstyle 6 exposes check convention via run()
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
        raw_content = (response.content or "").strip()
        content = _extract_all_python_code_blocks(raw_content) or raw_content
        # print(f"content for model {response.model}:\n{content}\n---")
        metadata: dict = {}
        print(f"========================================================================Scoring model {response.model} response: {response.error}")

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

        try:
            tree = ast.parse(content)
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
        complexity, complexity_meta = _complexity_score(content)
        tests_score, tests_meta = _tests_score(tree, len(content.splitlines()))
        style_score, style_meta = _style_score(content)
        doc_score, doc_meta = _documentation_score(tree, content)
        dead_code_score, dead_meta = _dead_code_score(content)
        security_score, sec_meta = _security_score(content)

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
