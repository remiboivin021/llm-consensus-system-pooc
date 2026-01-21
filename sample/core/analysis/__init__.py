"""Text analysis utilities - embeddings and similarity."""
from sample.core.analysis.embeddings import embed_text
from sample.core.analysis.similarity import cosine_similarity

__all__ = [
    "embed_text",
    "cosine_similarity"
]