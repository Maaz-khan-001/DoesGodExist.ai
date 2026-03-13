import hashlib
import os
import requests
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# HuggingFace MarianMT models for English → target language
HF_MODELS = {
    'ar': 'Helsinki-NLP/opus-mt-en-ar',
    'ur': 'Helsinki-NLP/opus-mt-en-ur',
}

# HuggingFace MarianMT models for target language → English (user input)
HF_REVERSE_MODELS = {
    'ar': 'Helsinki-NLP/opus-mt-ar-en',
    'ur': 'Helsinki-NLP/opus-mt-ur-en',
}


class TranslationService:
    """
    Translates GPT responses to Arabic or Urdu using HuggingFace free API.
    Also translates user input from Arabic/Urdu to English before RAG retrieval.

    L4 Cache: Redis, 7-day TTL. Applied to BOTH translation directions.

    RULES:
      - Never translate Quran Arabic — it is pre-stored and pre-verified.
      - Never crash debate flow on translation failure — return original English.
      - First call may be slow (HF model warm-up, 20–30s). Normal behavior.
      - Expect ~300–800ms per warm translation call. Document this UX tradeoff
        explicitly: Arabic/Urdu users face an extra ~600–1600ms per turn due to
        two translation calls (in + out). Cold starts add up to 30s.
    """
    CACHE_TTL = 86400 * 7    # 7 days
    HF_BASE = os.getenv('HF_API_URL', 'https://api-inference.huggingface.co/models')
    HF_TOKEN = os.getenv('HF_API_TOKEN', '')

    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate English text to target_lang (outbound: AI response).
        Returns original English on any failure.
        """
        if target_lang == 'en' or not text.strip():
            return text

        model = HF_MODELS.get(target_lang)
        if not model:
            return text    # unsupported language

        # L4: translation cache (outbound direction)
        cache_key = f'trans:out:{target_lang}:{hashlib.md5(text.encode()).hexdigest()}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        translated = self._call_hf(model, text)

        if translated:
            cache.set(cache_key, translated, self.CACHE_TTL)
            return translated

        return text    # fallback to English on failure

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translate user input from Arabic/Urdu to English before RAG retrieval.
        L4 cache is applied here too (inbound direction) to avoid redundant
        HuggingFace calls when the same phrase is repeated across turns.
        """
        if source_lang == 'en' or not text.strip():
            return text

        model = HF_REVERSE_MODELS.get(source_lang)
        if not model:
            return text

        # L4: translation cache (inbound direction — separate key namespace)
        cache_key = f'trans:in:{source_lang}:{hashlib.md5(text.encode()).hexdigest()}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        translated = self._call_hf(model, text)

        if translated:
            cache.set(cache_key, translated, self.CACHE_TTL)
            return translated

        return text    # fallback: pass original text if translation fails

    def _call_hf(self, model: str, text: str) -> str | None:
        """Call HuggingFace Inference API. Returns None on failure."""
        headers = {}
        if self.HF_TOKEN:
            headers['Authorization'] = f'Bearer {self.HF_TOKEN}'

        try:
            response = requests.post(
                f'{self.HF_BASE}/{model}',
                headers=headers,
                json={'inputs': text},
                timeout=30    # HF models can be slow on cold start
            )
            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and result:
                return result[0].get('translation_text')
            elif isinstance(result, dict) and 'error' in result:
                logger.warning(f'HuggingFace API error: {result["error"]}')
                return None

        except requests.exceptions.Timeout:
            logger.warning(f'HuggingFace translation timeout for model {model}')
        except Exception as e:
            logger.error(f'Translation failed: {e}')

        return None
