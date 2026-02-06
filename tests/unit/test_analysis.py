import pytest

from src.core.analysis.embeddings import embed_text
from src.core.analysis.similarity import cosine_similarity


def test_embed_text_empty_returns_zeros():
    vec = embed_text("")
    assert all(v == 0.0 for v in vec)
    assert len(vec) == 128


def test_embed_text_normalizes_tokens():
    vec = embed_text("a a b", dims=4)
    norm = sum(v * v for v in vec) ** 0.5
    assert pytest.approx(norm, rel=1e-6) == 1.0
    assert max(vec) > 0


def test_embed_text_zero_dims_returns_empty_norm():
    vec = embed_text("a", dims=0)
    assert vec == []


def test_cosine_similarity_happy_path():
    a = [1.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 1.0


def test_cosine_similarity_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_length_mismatch():
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 0.0])
