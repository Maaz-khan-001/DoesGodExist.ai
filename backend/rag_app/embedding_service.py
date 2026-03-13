import hashlib, os, logging
from django.core.cache import cache
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

logger = logging.getLogger(__name__)
EMBEDDING_BACKEND = os.getenv('EMBEDDING_BACKEND', 'openai')


# Dimensions by model — must match VectorField(dimensions=...) in DocumentChunk
_MODEL_DIMENSIONS = {
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 3072,
    'text-embedding-ada-002': 1536,
}
_LOCAL_DIMENSION = 384  # sentence-transformers default


def get_expected_dimension() -> int:
    """Return the embedding dimension for the currently configured backend/model."""
    if EMBEDDING_BACKEND == 'local':
        return _LOCAL_DIMENSION
    model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    return _MODEL_DIMENSIONS.get(model, 1536)

def get_embedding_service():
    if EMBEDDING_BACKEND == 'local':
        from .local_embedding_service import LocalEmbeddingService
        return LocalEmbeddingService()
    return EmbeddingService()

class EmbeddingService:
    CACHE_TTL = 86400 * 30
    BATCH_SIZE = 2048

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

    def get_embedding(self, text):
        key = f'emb:{self.model}:{hashlib.sha256(text.encode()).hexdigest()}'
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = self._call_api([text])[0]
        cache.set(key, result, self.CACHE_TTL)
        return result

    def get_batch_embeddings(self, texts):
        results = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            results.extend(self._call_api(texts[i:i+self.BATCH_SIZE]))
        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10),
           retry=retry_if_exception_type(openai.RateLimitError))
    def _call_api(self, texts):
        r = self.client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in sorted(r.data, key=lambda x: x.index)]