import logging
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F

logger = logging.getLogger(__name__)


class StreamingOrchestrator:
    """
    Async version of DebateOrchestrator that streams GPT tokens.

    Yields dicts:
      {'type': 'token',    'token': '...'}
      {'type': 'metadata', 'citations': [...], 'stage_advanced': bool,
                           'persona': '...', 'stage': '...'}
      {'type': 'error',    'message': '...', 'code': '...'}

    Architecture:
      - All DB operations are wrapped in sync_to_async
      - GPT streaming uses openai client's stream=True parameter
      - After streaming completes, metadata is saved to DB
    """

    async def stream(self, session, user_message: str):
        """Main entry point. Async generator — use with `async for`."""
        from django.core.cache import cache

        # 1. Budget check
        budget_cutoff = await sync_to_async(cache.get)('budget:cutoff_active')
        if budget_cutoff:
            yield {'type': 'error', 'message': 'Service paused', 'code': 'BUDGET_CUTOFF'}
            return

        # 2. Validate stage access
        try:
            await sync_to_async(self._validate_stage)(session)
        except Exception as e:
            yield {'type': 'error', 'message': str(e), 'code': 'STAGE_LOCKED'}
            return

        # 3. Detect persona
        persona = await sync_to_async(self._detect_persona)(session, user_message)

        # 4. Save user message + get sequence number
        seq = await sync_to_async(self._save_user_message)(session, user_message)

        # 5. Retrieve chunks
        chunks = await sync_to_async(self._retrieve_chunks)(session, user_message)

        # 6. Get history
        history = await sync_to_async(self._get_history)(session, seq)

        # 7. Build prompt
        prompt = await sync_to_async(self._build_prompt)(
            session, user_message, chunks, history
        )

        # 8. Route to model
        model, routing_reason = await sync_to_async(self._route)(session, seq)

        # 9. Stream GPT tokens
        full_content = ''
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = 0.0
        latency_ms = 0

        async for result in self._stream_gpt(prompt, model):
            if result['type'] == 'token':
                full_content += result['token']
                yield result
            elif result['type'] == 'stats':
                prompt_tokens = result['prompt_tokens']
                completion_tokens = result['completion_tokens']
                cost_usd = result['cost_usd']
                latency_ms = result['latency_ms']
            elif result['type'] == 'error':
                yield result
                return

        # 10. Save everything to DB (after streaming completes)
        stage_advanced, citations, new_stage = await sync_to_async(
            self._save_results
        )(
            session=session,
            user_message=user_message,
            full_content=full_content,
            chunks=chunks,
            seq=seq,
            model=model,
            routing_reason=routing_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

        # 11. Dispatch async tasks
        if seq == 0:
            await sync_to_async(self._dispatch_title_task)(session, user_message)

        # 12. Yield final metadata
        yield {
            'type': 'metadata',
            'citations': citations,
            'stage_advanced': stage_advanced,
            'persona': persona,
            'stage': new_stage,
        }

    async def _stream_gpt(self, prompt: dict, model: str):
        """Yields token events, then a stats event at the end."""
        import os
        import time
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        COST_PER_TOKEN = {
            'gpt-4o-mini': {'input': 0.00000015, 'output': 0.0000006},
            'gpt-4o':      {'input': 0.000005,   'output': 0.000015},
        }

        start = time.time()
        prompt_tokens = 0
        completion_tokens = 0

        try:
            stream = await client.chat.completions.create(
                model=model,
                max_tokens=800,
                temperature=0.3,
                stream=True,
                messages=[
                    {'role': 'system', 'content': prompt['system']},
                    {'role': 'user',   'content': prompt['user']},
                ],
                stream_options={'include_usage': True},
            )

            async for chunk in stream:
                # Token delta
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield {'type': 'token', 'token': delta.content}

                # Usage stats (sent in final chunk when include_usage=True)
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens

        except Exception as e:
            logger.error(f'OpenAI stream error: {e}', exc_info=True)
            yield {'type': 'error', 'message': 'AI service error', 'code': 'GPT_ERROR'}
            return

        latency_ms = int((time.time() - start) * 1000)
        rates = COST_PER_TOKEN.get(model, COST_PER_TOKEN['gpt-4o-mini'])
        cost = (prompt_tokens * rates['input']) + (completion_tokens * rates['output'])

        yield {
            'type': 'stats',
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'cost_usd': cost,
            'latency_ms': latency_ms,
        }

    # ── Sync helpers (called via sync_to_async) ─────────────────────────────

    def _validate_stage(self, session):
        from services.stage_validator import StageGateValidator
        StageGateValidator().validate(session)

    def _detect_persona(self, session, message):
        from services.persona_detector import PersonaDetector
        return PersonaDetector().detect_and_save(session, message)

    def _save_user_message(self, session, user_message):
        from debate_app.models import Message, DebateSession
        import tiktoken
        enc = tiktoken.encoding_for_model('gpt-4o-mini')
        token_count = len(enc.encode(user_message))
        with transaction.atomic():
            locked = DebateSession.objects.select_for_update().get(pk=session.pk)
            seq = locked.messages.count()
            Message.objects.create(
                session=locked,
                role='user',
                content=user_message,
                stage=locked.current_stage,
                sequence_num=seq,
                token_count=token_count,
            )
        return seq

    def _retrieve_chunks(self, session, user_message):
        from rag_app.retrieval_service import RetrievalService
        return RetrievalService().retrieve(
            query=user_message, stage=session.current_stage
        )

    def _get_history(self, session, seq):
        msgs = list(
            session.messages
            .filter(sequence_num__lt=seq)
            .order_by('-sequence_num')[:6]
        )
        msgs.reverse()
        return msgs

    def _build_prompt(self, session, user_message, chunks, history):
        from services.prompt_builder import PromptBuilder
        return PromptBuilder().build(session, user_message, chunks, history)

    def _route(self, session, seq):
        from services.complexity_router import ComplexityRouter
        from debate_app.models import Message
        last = Message.objects.filter(session=session, role='user').last()
        msg_text = last.content if last else ''
        return ComplexityRouter().route(msg_text, session, current_seq=seq)

    def _save_results(
        self, session, user_message, full_content, chunks, seq,
        model, routing_reason, prompt_tokens, completion_tokens,
        cost_usd, latency_ms,
    ):
        from debate_app.models import Message, DebateSession
        from analytics_app.models import GPTLog
        from services.stage_updater import StageUpdater

        with transaction.atomic():
            citations = self._build_citations(chunks)
            assistant_msg = Message.objects.create(
                session=session,
                role='assistant',
                content=full_content,
                stage=session.current_stage,
                token_count=completion_tokens,
                retrieved_chunk_ids=[str(c.id) for c in chunks],
                citations=citations,
                sequence_num=seq + 1,
            )
            GPTLog.objects.create(
                session=session,
                message=assistant_msg,
                model_used=model,
                routing_reason=routing_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                cache_hit=False,
            )
            DebateSession.objects.filter(pk=session.pk).update(
                total_cost_usd=F('total_cost_usd') + Decimal(str(cost_usd)),
                total_tokens=F('total_tokens') + (prompt_tokens + completion_tokens),
                total_turns=F('total_turns') + 1,
            )
            stage_advanced = StageUpdater().apply(session, user_message)

        session.refresh_from_db()
        return stage_advanced, citations, session.current_stage

    def _build_citations(self, chunks):
        citations = []
        for c in chunks:
            r = c.source_ref
            if c.chunk_type == 'quran':
                ref = f"Quran {r.get('surah')}:{r.get('ayah')}"
            elif c.chunk_type == 'hadith':
                ref = f"{r.get('collection')} #{r.get('number')}"
            else:
                ref = c.chunk_type.title()
            citations.append({
                'source_type': c.chunk_type,
                'reference': ref,
                'content': c.content[:300],
                'is_verified': c.is_verified,
            })
        return citations

    def _dispatch_title_task(self, session, user_message):
        try:
            from debate_app.tasks import generate_session_title
            generate_session_title.delay(str(session.id), user_message[:200])
        except Exception as e:
            logger.warning(f'Could not dispatch title task: {e}')
