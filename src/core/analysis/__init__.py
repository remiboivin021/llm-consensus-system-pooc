"""Text analysis utilities - embeddings and similarity."""
from src.core.analysis.embeddings import embed_text
from src.core.analysis.similarity import cosine_similarity

__all__ = [
    "embed_text",
    "cosine_similarity"
]