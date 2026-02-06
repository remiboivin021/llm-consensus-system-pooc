from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ModelResponse
from src.core.scoring import compute_scores


def test_compute_scores_identical_responses_yield_one():
    responses = [
        ModelResponse(model="m1", content="def foo():\n    return 1", latency_ms=100),
        ModelResponse(model="m2", content="def foo():\n    return 1", latency_ms=120),
    ]

    scores, stats = compute_scores(responses)

    assert all(detail.performance < 1.0 for detail in scores if not detail.error)
    assert all(detail.score <= 1.0 for detail in scores if not detail.error)
    assert stats.count == 2


def test_compute_scores_handles_single_valid_response():
    responses = [
        ModelResponse(
            model="m1",
            content=None,
            error=ErrorEnvelope(type="timeout", message="t", retryable=True),
        ),
        ModelResponse(model="m2", content="def only_one():\n    return 1"),
    ]

    scores, stats = compute_scores(responses)

    assert scores[0].error is True and scores[0].score == 0.0
    assert scores[1].error is False
    assert stats.count == 1
    assert stats.mean > 0.0
    assert stats.stddev == 0.0


def test_compute_scores_differs_for_different_content():
    responses = [
        ModelResponse(model="m1", content="def a(x):\n    if x:\n        return x\n    return 0"),
        ModelResponse(model="m2", content="def b():\n    return 42"),
        ModelResponse(
            model="m3",
            content="def c(n):\n    while n > 0:\n        n -= 1\n    return n",
        ),
    ]

    scores, stats = compute_scores(responses)

    non_error = [detail for detail in scores if not detail.error]
    assert any(detail.complexity < 1.0 for detail in non_error)
    assert stats.count == 3
    assert stats.max <= 1.0


def test_compute_scores_handles_markdown_code_block():
    markdown_content = """Here is code:

```python
def add(a, b):
    return a + b
```

And some explanation."""
    responses = [ModelResponse(model="m1", content=markdown_content, latency_ms=100)]

    scores, stats = compute_scores(responses)

    assert scores[0].error is False
    assert stats.count == 1
    assert scores[0].score > 0.0


def test_compute_scores_gracefully_handles_invalid_code():
    bad_content = "not python at all ```foo\n<xml>bad</xml>\n``` trailing text"
    responses = [ModelResponse(model="m1", content=bad_content, latency_ms=50)]

    scores, stats = compute_scores(responses)

    assert scores[0].error is True
    assert scores[0].score == 0.0
    assert stats.count == 0


def test_extract_code_from_json_decodes_escapes():
    json_like = r'''{
      "files": [
        {"filename": "main.py", "code": "def add(a, b):\\n    return a + b"}
      ]
    }'''
    responses = [ModelResponse(model="m1", content=json_like, latency_ms=10)]

    scores, stats = compute_scores(responses)

    assert scores[0].error is False
    assert stats.count == 1
    assert scores[0].score > 0.0
