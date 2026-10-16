"""
Adapter registry. Business logic imports `get_storage`, `get_vector_store`,
`get_ocr`, and `get_analyzer` — never a cloud SDK directly.
"""
from __future__ import annotations

import threading

from django.conf import settings

from .embeddings import EmbeddingBackend, HashingEmbedder
from .storage import AzureBlobStorage, LocalStorage, StorageBackend
from .vector import PgVectorStore, VectorStore

_lock = threading.Lock()
_storage: StorageBackend | None = None
_vector: VectorStore | None = None
_ocr = None
_embedder: EmbeddingBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    with _lock:
        if _storage is None:
            backend = settings.STORAGE_BACKEND
            if backend == "azure":
                _storage = AzureBlobStorage(
                    account_url=settings.AZURE_STORAGE_ACCOUNT_URL,
                    container=settings.AZURE_STORAGE_CONTAINER,
                    auth=settings.AZURE_STORAGE_AUTH,
                )
            else:
                _storage = LocalStorage(settings.LOCAL_STORAGE_DIR)
        return _storage


def get_vector_store() -> VectorStore:
    global _vector
    with _lock:
        if _vector is None:
            _vector = PgVectorStore()
        return _vector


def get_embedder() -> EmbeddingBackend:
    global _embedder
    with _lock:
        if _embedder is None:
            _embedder = HashingEmbedder(settings.EMBEDDING_DIM)
        return _embedder


def get_ocr():
    global _ocr
    with _lock:
        if _ocr is None:
            if settings.OCR_PROVIDER == "tesseract":
                try:
                    from .ocr import TesseractOcr

                    _ocr = TesseractOcr(settings.TESSERACT_CMD)
                except Exception:
                    from .ocr import NullOcr

                    _ocr = NullOcr()
            else:
                from .ocr import NullOcr

                _ocr = NullOcr()
        return _ocr


def reset_adapters() -> None:
    """Test helper to force adapter re-initialization."""
    global _storage, _vector, _ocr, _embedder
    with _lock:
        _storage = _vector = _ocr = _embedder = None
