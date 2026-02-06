# from src.contracts.errors import ErrorEnvelope
# from src.contracts.response import ModelResponse, ScoreDetail
# from src.core.consensus import compute_consensus


# def test_compute_consensus_picks_most_similar():
#     responses = [
#         ModelResponse(model="model-a", content="foo bar baz"),
#         ModelResponse(model="model-b", content="foo bar baz"),
#         ModelResponse(model="model-c", content="unrelated text goes here"),
#     ]

#     winner, confidence, method = compute_consensus(responses)

#     assert winner == "model-a"
#     assert 0.0 <= confidence <= 1.0
#     assert method == "majority_cosine"


# def test_compute_consensus_handles_single_success():
#     responses = [
#         ModelResponse(
#             model="model-a",
#             content=None,
#             error=ErrorEnvelope(type="timeout", message="t", retryable=True),
#         ),
#         ModelResponse(model="model-b", content="only response"),
#     ]

#     winner, confidence, _ = compute_consensus(responses)

#     assert winner == "model-b"
#     assert confidence == 0.33


# def test_compute_consensus_prefers_score_when_provided():
#     responses = [
#         ModelResponse(model="model-a", content="foo"),
#         ModelResponse(model="model-b", content="bar"),
#     ]
#     scores = [
#         ScoreDetail(
#             model="model-a",
#             performance=0.2,
#             complexity=0.2,
#             tests=0.2,
#             style=0.2,
#             documentation=0.2,
#             dead_code=0.2,
#             security=0.2,
#             score=0.3,
#             error=False,
#         ),
#         ScoreDetail(
#             model="model-b",
#             performance=0.9,
#             complexity=0.9,
#             tests=0.9,
#             style=0.9,
#             documentation=0.9,
#             dead_code=0.9,
#             security=0.9,
#             score=0.9,
#             error=False,
#         ),
#     ]

#     winner, confidence, method = compute_consensus(responses, scores=scores)

#     assert winner == "model-b"
#     assert method == "quality_score"
#     assert confidence > 0.5


# def test_compute_consensus_score_fallbacks_when_all_scores_error():
#     responses = [
#         ModelResponse(model="model-a", content="foo bar baz"),
#         ModelResponse(model="model-b", content="foo bar baz"),
#     ]
#     error_scores = [
#         ScoreDetail(
#             model="model-a",
#             performance=0.0,
#             complexity=0.0,
#             tests=0.0,
#             style=0.0,
#             documentation=0.0,
#             dead_code=0.0,
#             security=0.0,
#             score=0.0,
#             error=True,
#         ),
#         ScoreDetail(
#             model="model-b",
#             performance=0.0,
#             complexity=0.0,
#             tests=0.0,
#             style=0.0,
#             documentation=0.0,
#             dead_code=0.0,
#             security=0.0,
#             score=0.0,
#             error=True,
#         ),
#     ]

#     winner, confidence, method = compute_consensus(responses, scores=error_scores)

#     assert winner == "model-a"
#     assert method == "majority_cosine"
#     assert 0.0 <= confidence <= 1.0
