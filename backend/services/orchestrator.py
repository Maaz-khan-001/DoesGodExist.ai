import logging
import threading
import tiktoken
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Max
from django.conf import settings
from django.core.cache import cache
from debate_app.models import DebateSession, Message
from analytics_app.models import GPTLog
from rag_app.retrieval_service import RetrievalService
from .stage_validator import StageGateValidator, StageNotUnlocked
from .stage_updater import StageUpdater
from .complexity_router import ComplexityRouter
from .prompt_builder import PromptBuilder
from .gpt_client import GPTClient
from .persona_detector import PersonaDetector

logger = logging.getLogger(__name__)

BUDGET_CUTOFF_REDIS_KEY = 'budget:cutoff_active'

TIER_MAX_TOKENS = {
    'anonymous': 600,
    'registered': 800,
    'premium': 1500,
}

_ENCODING = None

def _get_encoding():
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.encoding_for_model('gpt-4o-mini')
    return _ENCODING

def count_tokens(text: str) -> int:
    try:
        return len(_get_encoding().encode(text))
    except Exception:
        return len(text.split())


# ---------------------------------------------------------------------------
# Per-session threading lock registry
#
# WHY: (session_id, sequence_num) has a UNIQUE constraint. Under concurrent
# requests for the same session, two threads can read the same MAX(sequence_num)
# before either commits and both try to insert with the same sequence number.
#
# select_for_update() serializes at the DB level but Django's test client with
# transaction=True can share a DB connection across threads, undermining row
# locks. A process-level threading.Lock keyed by session_id is the correct
# and portable solution for single-process deployments (gunicorn threaded mode).
#
# For multi-process deployments, replace with a Redis lock.
# ---------------------------------------------------------------------------
_session_locks: dict[str, threading.Lock] = {}
_session_locks_mutex = threading.Lock()

def _get_session_lock(session_id: str) -> threading.Lock:
    with _session_locks_mutex:
        if session_id not in _session_locks:
            _session_locks[session_id] = threading.Lock()
        return _session_locks[session_id]


class BudgetCutoffActive(Exception):
    pass


class DebateOrchestrator:
    """
    Runs a full debate turn. Concurrency-safe via per-session threading.Lock.

    CONCURRENCY DESIGN:
    -------------------
    Problem: (session_id, sequence_num) has a UNIQUE constraint. Concurrent
    requests for the same session race to assign sequence numbers.

    Solution: A per-session threading.Lock ensures only one thread at a time
    reads MAX(sequence_num) and inserts new messages for a given session.
    The lock is held only during the DB reads/writes — GPT call happens outside.
    """

    def run(
        self,
        session: DebateSession,
        user_message: str,
        original_message: str = None,
    ) -> tuple[Message, bool, str]:
        # 1. Budget cutoff check
        if cache.get(BUDGET_CUTOFF_REDIS_KEY):
            raise BudgetCutoffActive()

        # 2. Validate stage access
        StageGateValidator().validate(session)

        # 3. Detect and save persona
        detect_text = original_message or user_message
        persona = PersonaDetector().detect_and_save(session, detect_text)

        # 4. Acquire per-session lock and reserve sequence numbers.
        #    Lock is released after both user msg and assistant placeholder
        #    are committed, so the next thread reads the correct MAX.
        session_lock = _get_session_lock(str(session.pk))

        with session_lock:
            with transaction.atomic():
                locked_session = DebateSession.objects.select_for_update().get(pk=session.pk)

                max_seq = locked_session.messages.aggregate(m=Max('sequence_num'))['m']
                seq = (max_seq + 1) if max_seq is not None else 0

                user_token_count = count_tokens(user_message)
                user_msg = Message.objects.create(
                    session=locked_session,
                    role='user',
                    content=user_message,
                    stage=locked_session.current_stage,
                    sequence_num=seq,
                    token_count=user_token_count,
                )

                # Reserve seq+1 with a placeholder so the next thread's MAX
                # reflects both rows and starts at seq+2.
                assistant_placeholder = Message.objects.create(
                    session=locked_session,
                    role='assistant',
                    content='__pending__',
                    stage=locked_session.current_stage,
                    sequence_num=seq + 1,
                    token_count=0,
                )

        session = locked_session

        # 5. Retrieve relevant chunks (lock released — no contention)
        chunks = RetrievalService().retrieve(
            query=user_message,
            stage=session.current_stage,
        )

        # 6. Fetch history (exclude placeholder — content='__pending__')
        history = list(
            session.messages
            .filter(sequence_num__lt=seq, role__in=['user', 'assistant'])
            .exclude(content='__pending__')
            .order_by('-sequence_num')[:6]
        )
        history.reverse()

        # 7. Build prompt
        prompt = PromptBuilder().build(
            session=session,
            user_message=user_message,
            chunks=chunks,
            history=history,
        )

        # 8. Route to model
        model, routing_reason = ComplexityRouter().route(
            user_message, session, current_seq=seq
        )
        max_tokens = TIER_MAX_TOKENS.get(session.user.tier, 600)

        # 9. Call GPT (outside lock and transaction — can take seconds)
        gpt_response = GPTClient().complete(prompt, model, max_tokens)

        complexity = 1.0 if model == 'gpt-4o' else 0.3

        # 10. Update placeholder with real content + save all side-effects.
        #     sequence_num is NOT touched — already committed in step 4.
        stage_advanced = False

        with transaction.atomic():
            citations = self._build_citations(chunks)

            Message.objects.filter(pk=assistant_placeholder.pk).update(
                content=gpt_response.content,
                token_count=gpt_response.completion_tokens,
                retrieved_chunk_ids=[str(c.id) for c in chunks],
                citations=citations,
            )
            assistant_placeholder.refresh_from_db()
            assistant_msg = assistant_placeholder

            GPTLog.objects.create(
                session=session,
                message=assistant_msg,
                model_used=model,
                routing_reason=routing_reason,
                prompt_tokens=gpt_response.prompt_tokens,
                completion_tokens=gpt_response.completion_tokens,
                total_tokens=gpt_response.prompt_tokens + gpt_response.completion_tokens,
                cost_usd=gpt_response.cost_usd,
                latency_ms=gpt_response.latency_ms,
                cache_hit=gpt_response.from_cache,
                cache_layer='L3' if gpt_response.from_cache else None,
            )

            DebateSession.objects.filter(pk=session.pk).update(
                total_cost_usd=F('total_cost_usd') + Decimal(str(gpt_response.cost_usd)),
                total_tokens=F('total_tokens') + (gpt_response.prompt_tokens + gpt_response.completion_tokens),
                total_turns=F('total_turns') + 1,
                complexity_score=complexity,
            )

            stage_advanced = StageUpdater().apply(session, detect_text)

        # 11. Dispatch async Celery tasks
        self._dispatch_async_tasks(session, seq, detect_text, stage_advanced)

        session.refresh_from_db()

        return assistant_msg, stage_advanced, persona

    def _build_citations(self, chunks) -> list:
        citations = []
        for c in chunks:
            ref = self._format_ref(c)
            citations.append({
                'source_type': c.chunk_type,
                'reference': ref,
                'content': c.content[:300],
                'is_verified': c.is_verified,
            })
        return citations

    def _format_ref(self, chunk) -> str:
        r = chunk.source_ref
        if chunk.chunk_type == 'quran':
            return f"Quran {r.get('surah')}:{r.get('ayah')} [Verified]"
        if chunk.chunk_type == 'hadith':
            return f"{r.get('collection')} #{r.get('number')}, Grade: {r.get('grade')}"
        return chunk.chunk_type.title()

    def _dispatch_async_tasks(self, session, seq, user_message, stage_advanced):
        if seq == 0:
            try:
                from debate_app.tasks import generate_session_title
                generate_session_title.delay(str(session.id), user_message[:200])
            except Exception as e:
                logger.warning(f'Could not dispatch generate_session_title: {e}')

        if stage_advanced:
            try:
                from debate_app.tasks import notify_stage_advanced
                notify_stage_advanced.delay(str(session.id))
            except Exception as e:
                logger.warning(f'Could not dispatch notify_stage_advanced: {e}')