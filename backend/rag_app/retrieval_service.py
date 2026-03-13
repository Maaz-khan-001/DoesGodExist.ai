import hashlib, logging
from django.core.cache import cache
from pgvector.django import CosineDistance
from .models import DocumentChunk
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class RetrievalService:
    # is_verified=True is re-applied on EVERY fetch, even cache hits.
    # This prevents stale unverified chunks from being served if a chunk
    # loses its verified status after it was cached in Redis.
    CACHE_TTL = 86400

    def __init__(self):
        self.emb_svc = get_embedding_service()

    def retrieve(self, query, stage, top_k=8, token_budget=2500):
        cache_key = f'ret:{stage}:{hashlib.sha256(query.encode()).hexdigest()}'
        cached_ids = cache.get(cache_key)

        if cached_ids is not None:
            chunks = list(DocumentChunk.objects.filter(
                id__in=cached_ids,
                is_verified=True,       # re-applied on cache hit
                deleted_at__isnull=True
            ))
            if chunks:
                return self._apply_budget(chunks, token_budget)

        try:
            embedding = self.emb_svc.get_embedding(query)
        except Exception as e:
            logger.error(f'Embedding failed: {e}')
            return []

        chunks = list(
            DocumentChunk.objects
            .filter(stage_tags__contains=[stage], is_verified=True,
                    deleted_at__isnull=True)
            .exclude(embedding=None)
            .order_by(CosineDistance('embedding', embedding))[:top_k]
        )
        cache.set(cache_key, [str(c.id) for c in chunks], self.CACHE_TTL)
        return self._apply_budget(chunks, token_budget)

    def _apply_budget(self, chunks, budget):
        selected, used = [], 0
        for c in chunks:
            if used + c.token_count + 30 > budget:
                break
            selected.append(c)
            used += c.token_count
        return selected
