import hashlib, logging
from django.core.cache import cache

logger = logging.getLogger(__name__)
_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError('Run: pip install sentence-transformers (dev only)')
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

class LocalEmbeddingService:
    # 384 dimensions - NOT compatible with 1536-dim production embeddings
    # When switching to OpenAI production:
    #   DocumentChunk.objects.all().update(embedding=None)
    #   Re-run embed_chunks Celery task
    CACHE_TTL = 86400

    def get_embedding(self, text):
        key = f'local_emb:{hashlib.sha256(text.encode()).hexdigest()}'
        cached = cache.get(key)
        if cached:
            return cached
        emb = _get_model().encode(text).tolist()
        cache.set(key, emb, self.CACHE_TTL)
        return emb

    def get_batch_embeddings(self, texts):
        return _get_model().encode(texts).tolist()
