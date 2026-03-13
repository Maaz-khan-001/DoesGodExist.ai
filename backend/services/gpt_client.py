import hashlib
import json
import os
import time
import logging
from django.core.cache import cache
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

logger = logging.getLogger(__name__)

COST_PER_TOKEN = {
    'gpt-4o-mini': {'input': 0.00000015, 'output': 0.0000006},
    'gpt-4o':      {'input': 0.000005,   'output': 0.000015},
}


class GPTResponse:
    """
    FIX: Plain class instead of dataclass to support JSON serialization for Redis.
    """
    __slots__ = ['content', 'model', 'prompt_tokens', 'completion_tokens',
                 'cost_usd', 'latency_ms', 'from_cache']

    def __init__(self, content, model, prompt_tokens, completion_tokens,
                 cost_usd, latency_ms, from_cache=False):
        self.content = content
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.from_cache = from_cache

    def to_dict(self):
        """FIX: JSON-serializable dict for Redis caching."""
        return {
            'content': self.content,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'cost_usd': self.cost_usd,
            'latency_ms': self.latency_ms,
        }

    @classmethod
    def from_dict(cls, d: dict, from_cache: bool = True):
        """Reconstruct from cached dict."""
        return cls(from_cache=from_cache, **d)


class GPTClient:
    """
    OpenAI API wrapper with:
      - L3 Redis response cache (6-hour TTL, JSON serialization)
      - Automatic cost calculation
      - Retry on rate limits (3 attempts, exponential backoff)
      - Latency tracking
    """
    CACHE_TTL = 21600  # 6 hours

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def complete(
        self,
        prompt: dict,
        model: str,
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> GPTResponse:
        cache_key = f'resp:v1:{hashlib.sha256(str(prompt).encode()).hexdigest()}'

        # FIX: Cache stored as JSON string, not pickle object
        cached_json = cache.get(cache_key)
        if cached_json is not None:
            try:
                cached_dict = json.loads(cached_json)
                return GPTResponse.from_dict(cached_dict, from_cache=True)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f'Cache deserialization failed: {e}. Re-fetching.')
                cache.delete(cache_key)

        return self._call_api(prompt, model, max_tokens, temperature, cache_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(openai.RateLimitError)
    )
    def _call_api(
        self,
        prompt: dict,
        model: str,
        max_tokens: int,
        temperature: float,
        cache_key: str,
    ) -> GPTResponse:
        start = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {'role': 'system', 'content': prompt['system']},
                    {'role': 'user',   'content': prompt['user']},
                ]
            )
        except openai.RateLimitError:
            logger.warning(f'OpenAI rate limit hit for model {model}')
            raise
        except openai.APIError as e:
            logger.error(f'OpenAI API error: {e}')
            raise

        latency = int((time.time() - start) * 1000)
        content = response.choices[0].message.content
        p_tok = response.usage.prompt_tokens
        c_tok = response.usage.completion_tokens

        if model not in COST_PER_TOKEN:
            logger.warning(
                f'Unknown model "{model}" — using gpt-4o-mini rates for cost calc.'
            )
        rates = COST_PER_TOKEN.get(model, COST_PER_TOKEN['gpt-4o-mini'])
        cost = (p_tok * rates['input']) + (c_tok * rates['output'])

        result = GPTResponse(
            content=content,
            model=model,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            cost_usd=cost,
            latency_ms=latency,
        )

        # FIX: Cache as JSON string (not pickle)
        cache.set(cache_key, json.dumps(result.to_dict()), self.CACHE_TTL)
        return result