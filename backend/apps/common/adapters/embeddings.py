"""Deterministic, offline embedding adapter.

The default uses scikit-learn's feature hashing so local development and tests
need no external model and produce stable vectors. A cloud embedding model can
be substituted behind the same interface later.
"""
from __future__ import annotations

import abc



class EmbeddingBackend(abc.ABC):
    dim: int

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder(EmbeddingBackend):
    def __init__(self, dim: int):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.dim = dim
        self._vec = HashingVectorizer(
            n_features=dim,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self._vec.transform(texts)
        dense = matrix.toarray() if hasattr(matrix, "toarray") else matrix
        return [row.astype("float32").tolist() for row in dense]
