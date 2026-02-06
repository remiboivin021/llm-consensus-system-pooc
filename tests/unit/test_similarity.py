from src.core.analysis.similarity import cosine_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 2, 3], [1, 2, 3]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9
