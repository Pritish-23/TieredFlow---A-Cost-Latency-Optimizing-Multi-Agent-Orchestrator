import logging
import uuid
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    query_id: str
    query_text: str
    response_text: str
    embedding: np.ndarray
    tier_used: str
    cost_usd: float


@dataclass
class CacheLookupResult:
    found: bool
    similarity_score: float = 0.0
    matched_query_id: Optional[str] = None
    cached_response: Optional[str] = None


class SemanticCache:

    def __init__(
        self,
        similarity_high: float = 0.92,
        similarity_mid: float = 0.75,
    ):
        self.similarity_high = similarity_high
        self.similarity_mid = similarity_mid
        self._entries: list[CacheEntry] = []
        self._model = None

    def _load_model(self):
        if self._model is None:
            logger.info("[Cache] Loading sentence-transformer model...")
            from sentence_transformers import (
                SentenceTransformer,
            )

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[Cache] Model loaded.")

    def _embed(self, text: str) -> np.ndarray:
        self._load_model()
        emb = self._model.encode([text], normalize_embeddings=True)
        return emb[0].astype("float32")

    def lookup(self, query: str) -> CacheLookupResult:
        if not self._entries:
            return CacheLookupResult(found=False)

        query_emb = self._embed(query)

        best_score = -1.0
        best_entry = None

        for entry in self._entries:
            score = float(np.dot(query_emb, entry.embedding))
            if score > best_score:
                best_score = score
                best_entry = entry

        logger.info(f"[Cache] Best similarity: {best_score:.4f}")

        if best_score >= self.similarity_mid:
            return CacheLookupResult(
                found=True,
                similarity_score=best_score,
                matched_query_id=best_entry.query_id,
                cached_response=best_entry.response_text,
            )

        return CacheLookupResult(found=False, similarity_score=best_score)

    def store(
        self,
        query: str,
        response: str,
        tier_used: str,
        cost_usd: float,
    ) -> str:
        emb = self._embed(query)
        entry = CacheEntry(
            query_id=str(uuid.uuid4())[:8],
            query_text=query,
            response_text=response,
            embedding=emb,
            tier_used=tier_used,
            cost_usd=cost_usd,
        )
        self._entries.append(entry)
        logger.info(
            f"[Cache] Stored entry {entry.query_id}. Total: {len(self._entries)}"
        )
        return entry.query_id

    @property
    def size(self) -> int:
        return len(self._entries)


_cache_instance: Optional[SemanticCache] = None


def get_cache() -> SemanticCache:
    global _cache_instance
    if _cache_instance is None:
        from config.settings import settings

        _cache_instance = SemanticCache(
            similarity_high=settings.cache_similarity_high,
            similarity_mid=settings.cache_similarity_mid,
        )
    return _cache_instance
