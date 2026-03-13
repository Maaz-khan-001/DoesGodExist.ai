
import json
import logging
import asyncio
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# SSE content type
SSE_CONTENT_TYPE = 'text/event-stream'

# Headers required for SSE
SSE_HEADERS = {
    'Cache-Control': 'no-cache',
    'X-Accel-Buffering': 'no',    # Disable Nginx buffering for SSE
    'Access-Control-Allow-Origin': '*',  # Adjust for your CORS setup
}


def format_sse_event(data: dict, event: str = None) -> str:
    """Format a dict as an SSE event string."""
    lines = []
    if event:
        lines.append(f'event: {event}')
    lines.append(f'data: {json.dumps(data)}')
    lines.append('')   # Empty line = end of event
    lines.append('')
    return '\n'.join(lines)


@method_decorator(csrf_exempt, name='dispatch')
class DebateStreamView(View):
    """
    POST /api/v1/debate/message/stream/

    Streams GPT tokens as Server-Sent Events (SSE).
    Each token is sent as an SSE event with:
      data: {"token": "word "}

    On completion:
      data: {"done": true, "session_id": "...", "stage": "...",
              "stage_advanced": false, "citations": [...], "persona": "..."}

    On error:
      data: {"error": "message", "code": "ERROR_CODE"}

    FRONTEND USAGE:
      const response = await fetch('/api/v1/debate/message/stream/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message, session_id }),
        credentials: 'include',
      })
      const reader = response.body.getReader()
      // Read tokens and append to message content

    NOTE: This view requires Django ASGI + async-capable server.
    Standard Gunicorn (sync) workers will NOT stream correctly.
    Use: gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker
    """

    async def post(self, request):
        import json as json_mod

        # Parse request body
        try:
            body = json_mod.loads(request.body)
        except (json_mod.JSONDecodeError, ValueError):
            return StreamingHttpResponse(
                self._error_stream('Invalid JSON body', 'INVALID_JSON'),
                content_type=SSE_CONTENT_TYPE,
                status=400,
                headers=SSE_HEADERS,
            )

        message = body.get('message', '').strip()
        session_id = body.get('session_id')
        language = body.get('language', 'en')
        debate_mode = body.get('debate_mode', 'standard')

        if not message:
            return StreamingHttpResponse(
                self._error_stream('Message is required', 'MISSING_MESSAGE'),
                content_type=SSE_CONTENT_TYPE,
                status=400,
                headers=SSE_HEADERS,
            )

        if len(message) > 2000:
            return StreamingHttpResponse(
                self._error_stream('Message too long (max 2000 chars)', 'MESSAGE_TOO_LONG'),
                content_type=SSE_CONTENT_TYPE,
                status=400,
                headers=SSE_HEADERS,
            )

        # Get user (sync DB call wrapped in sync_to_async)
        try:
            user, session = await sync_to_async(self._get_user_and_session)(
                request, session_id, debate_mode
            )
        except Exception as e:
            logger.error(f'Stream setup error: {e}', exc_info=True)
            return StreamingHttpResponse(
                self._error_stream('Session error', 'SESSION_ERROR'),
                content_type=SSE_CONTENT_TYPE,
                status=400,
                headers=SSE_HEADERS,
            )

        # Check and increment turn (sync DB call)
        can_proceed = await sync_to_async(self._check_turn_limit)(user)
        if not can_proceed:
            return StreamingHttpResponse(
                self._error_stream('Daily limit reached', 'DAILY_LIMIT_REACHED'),
                content_type=SSE_CONTENT_TYPE,
                status=429,
                headers=SSE_HEADERS,
            )

        return StreamingHttpResponse(
            self._stream_response(request, session, message, language),
            content_type=SSE_CONTENT_TYPE,
            headers=SSE_HEADERS,
        )

    async def _stream_response(self, request, session, message, language):
        """
        Async generator that yields SSE events.
        Uses orchestrator_stream.py for the actual streaming logic.
        """
        from services.orchestrator_stream import StreamingOrchestrator

        try:
            orchestrator = StreamingOrchestrator()

            # Send a "start" event so frontend knows streaming has begun
            yield format_sse_event({'status': 'started'}, event='start')

            full_content = ''
            citations = []
            stage_advanced = False
            persona = 'skeptic'
            new_stage = session.current_stage

            # Stream tokens from orchestrator
            async for event in orchestrator.stream(
                session=session,
                user_message=message,
            ):
                event_type = event.get('type')

                if event_type == 'token':
                    token = event['token']
                    full_content += token
                    yield format_sse_event({'token': token})

                elif event_type == 'metadata':
                    # Final metadata from orchestrator after streaming completes
                    citations = event.get('citations', [])
                    stage_advanced = event.get('stage_advanced', False)
                    persona = event.get('persona', 'skeptic')
                    new_stage = event.get('stage', session.current_stage)

                elif event_type == 'error':
                    yield format_sse_event(
                        {'error': event.get('message', 'Unknown error'),
                         'code': event.get('code', 'STREAM_ERROR')},
                        event='error'
                    )
                    return

            # Send completion event with full metadata
            yield format_sse_event({
                'done': True,
                'session_id': str(session.id),
                'stage': new_stage,
                'stage_advanced': stage_advanced,
                'persona': persona,
                'citations': citations,
            }, event='done')

        except Exception as e:
            logger.error(f'Streaming error: {e}', exc_info=True)
            yield format_sse_event(
                {'error': 'Stream interrupted', 'code': 'STREAM_ERROR'},
                event='error'
            )

    def _get_user_and_session(self, request, session_id, debate_mode):
        """Sync helper — called via sync_to_async."""
        from debate_app.models import User, DebateSession

        # Get user
        if request.user.is_authenticated:
            user = request.user
        else:
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            user, _ = User.objects.get_or_create(
                session_key=session_key,
                defaults={'is_anonymous_user': True, 'tier': 'anonymous'}
            )

        # Get or create session
        if session_id:
            session = DebateSession.objects.get(
                id=session_id, user=user, deleted_at__isnull=True
            )
        else:
            session = DebateSession.objects.create(
                user=user, debate_mode=debate_mode
            )

        return user, session

    def _check_turn_limit(self, user):
        """Sync helper — called via sync_to_async."""
        from django.utils import timezone
        from django.db.models import F
        from debate_app.models import User

        LIMITS = {'anonymous': 5, 'registered': 20, 'premium': 9999}
        today = timezone.now().date()
        limit = LIMITS.get(user.tier, 5)

        if user.daily_reset_date != today:
            User.objects.filter(pk=user.pk).update(
                daily_turn_count=0, daily_reset_date=today
            )
            user.daily_turn_count = 0

        updated = User.objects.filter(
            pk=user.pk, daily_turn_count__lt=limit
        ).update(daily_turn_count=F('daily_turn_count') + 1)
        return updated > 0

    def _error_stream(self, message, code):
        """Yield a single SSE error event then stop."""
        yield format_sse_event({'error': message, 'code': code}, event='error')

