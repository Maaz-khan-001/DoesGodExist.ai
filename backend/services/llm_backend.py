"""
LLM Backend abstraction layer.

Provides a consistent interface for interacting with different LLM providers.
Currently only OpenAI is implemented, but this layer allows adding:
  - Anthropic Claude (claude-3-opus)
  - Google Gemini
  - Local LLMs (Ollama)
  - Azure OpenAI

Usage in gpt_client.py:
  from services.llm_backend import get_llm_backend
  backend = get_llm_backend()
  response = backend.complete(messages, model, max_tokens, temperature)
"""

import os
import logging

logger = logging.getLogger(__name__)

LLM_BACKEND = os.getenv('LLM_BACKEND', 'openai')


def get_llm_backend():
    """Factory function — returns the configured LLM backend."""
    if LLM_BACKEND == 'openai':
        return OpenAIBackend()
    raise ValueError(
        f'Unknown LLM_BACKEND: "{LLM_BACKEND}". '
        f'Supported values: openai'
    )


class OpenAIBackend:
    """
    OpenAI GPT backend.
    Wraps the OpenAI client with consistent error handling.

    In practice, the GPTClient class in gpt_client.py handles
    caching and cost calculation on top of this backend.
    """

    SUPPORTED_MODELS = {
        'gpt-4o-mini',
        'gpt-4o',
    }

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def complete(
        self,
        messages: list,
        model: str = 'gpt-4o-mini',
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> dict:
        """
        Calls the OpenAI Chat Completions API.

        Returns:
          {
            'content': str,
            'prompt_tokens': int,
            'completion_tokens': int,
            'model': str,
          }
        """
        if model not in self.SUPPORTED_MODELS:
            logger.warning(
                f'Unknown model "{model}" requested. Falling back to gpt-4o-mini.'
            )
            model = 'gpt-4o-mini'

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            'content': response.choices[0].message.content,
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'model': response.model,
        }
