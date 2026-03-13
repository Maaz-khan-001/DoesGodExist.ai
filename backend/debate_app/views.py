import logging
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import User, DebateSession, Message
from .serializers import (
    DebateMessageInputSerializer,
    DebateSessionListSerializer,
    DebateSessionDetailSerializer,
)
from services.orchestrator import DebateOrchestrator, BudgetCutoffActive
from services.stage_validator import StageNotUnlocked
from services.translation_service import TranslationService

logger = logging.getLogger(__name__)

DAILY_TURN_LIMITS = {
    'anonymous': 5,
    'registered': 20,
    'premium': 9999,
}


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'
    rate = '5/min'


class RegisterRateThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '3/min'


class DebateAnonThrottle(AnonRateThrottle):
    rate = '10/min'


class DebateUserThrottle(UserRateThrottle):
    rate = '60/min'


class DebateMessageView(APIView):
    """
    POST /api/v1/debate/message/
    Main debate endpoint. Handles anonymous and authenticated users.
    """
    permission_classes = [AllowAny]
    throttle_classes = [DebateAnonThrottle, DebateUserThrottle]

    def post(self, request):
        serializer = DebateMessageInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": "VALIDATION_ERROR", "errors": serializer.errors},
                status=400
            )

        data = serializer.validated_data
        language = data.get('language', 'en')
        user_message = data['message']

        # Get or create user and session
        try:
            session = self._get_or_create_session(request, data)
        except DebateSession.DoesNotExist:
            return Response(
                {'error': 'Session not found.', 'code': 'SESSION_NOT_FOUND'},
                status=404
            )

        # Update debate mode if changed
        if 'debate_mode' in data and data['debate_mode'] != session.debate_mode:
            session.debate_mode = data['debate_mode']
            session.save(update_fields=['debate_mode'])

        # FIX: Atomic turn limit check using F() to prevent race condition
        if not self._check_and_increment_turn_atomic(session.user):
            return Response({
                'error': 'Daily limit reached.',
                'code': 'DAILY_LIMIT_REACHED',
                'detail': 'Register for a free account to get 20 turns per day.',
                'upgrade_required': True,
            }, status=429)

        # Update last_active_at
        User.objects.filter(pk=session.user.pk).update(last_active_at=timezone.now())

        # Translate user input to English for RAG retrieval
        retrieval_message = user_message
        if language != 'en':
            retrieval_message = TranslationService().translate_to_english(
                user_message, language
            )

        try:
            assistant_msg, stage_advanced, persona = DebateOrchestrator().run(
                session=session,
                user_message=retrieval_message,
                original_message=user_message,
            )
        except StageNotUnlocked as e:
            return Response(
                {'error': str(e), 'code': 'STAGE_LOCKED', 'stage_locked': True},
                status=400
            )
        except BudgetCutoffActive:
            return Response({
                'error': 'Service temporarily paused due to high usage. Please try again tomorrow.',
                'code': 'BUDGET_CUTOFF',
            }, status=503)
        except Exception:
            logger.error('Debate orchestrator error', exc_info=True)
            return Response(
                {'error': 'Service temporarily unavailable.', 'code': 'SERVER_ERROR'},
                status=503
            )

        # Translate AI response to user's language
        content = assistant_msg.content
        if language != 'en':
            content = TranslationService().translate(content, language)

        # Reload session for authoritative stage after StageUpdater
        session.refresh_from_db()

        return Response({
            'message_id': str(assistant_msg.id),
            'content': content,
            'stage': session.current_stage,
            'session_id': str(session.id),
            'stage_advanced': stage_advanced,
            'debate_mode': session.debate_mode,
            'citations': assistant_msg.citations,       # FIX: now returned
            'persona': persona,                          # FIX: now returned
            'turn_number': session.total_turns,          # NEW
        }, status=200)

    def _get_or_create_session(self, request, data):
        user = self._get_or_create_user(request)

        if data.get('session_id'):
            # Ownership check: prevents session hijacking
            session = DebateSession.objects.get(
                id=data['session_id'],
                user=user,
                deleted_at__isnull=True,
            )
            return session

        return DebateSession.objects.create(
            user=user,
            debate_mode=data.get('debate_mode', 'standard')
        )

    def _get_or_create_user(self, request):
        if request.user.is_authenticated:
            return request.user

        # Anonymous user — tracked by Django session key
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        user, _ = User.objects.get_or_create(
            session_key=session_key,
            defaults={'is_anonymous_user': True, 'tier': 'anonymous'}
        )
        return user

    def _check_and_increment_turn_atomic(self, user: User) -> bool:
        """
        FIX: Atomic turn limit check using F() expression.
        Prevents the TOCTOU race condition where two concurrent requests
        both read the same count and both pass the limit check.

        Strategy:
          1. Reset count if new day (non-atomic but safe — only sets to 0)
          2. Attempt atomic increment only if under limit
          3. If 0 rows updated = limit reached, return False
        """
        today = timezone.now().date()
        limit = DAILY_TURN_LIMITS.get(user.tier, 5)

        # Reset counter for new day
        if user.daily_reset_date != today:
            User.objects.filter(pk=user.pk).update(
                daily_turn_count=0,
                daily_reset_date=today,
            )
            user.daily_turn_count = 0
            user.daily_reset_date = today

        # Atomic increment: only updates if count is still below limit
        # Returns number of rows updated (0 = limit reached, 1 = success)
        updated = User.objects.filter(
            pk=user.pk,
            daily_turn_count__lt=limit,
        ).update(
            daily_turn_count=F('daily_turn_count') + 1
        )
        return updated > 0


class DebateSessionListView(APIView):
    """GET /api/v1/debate/sessions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = DebateSession.objects.filter(
            user=request.user,
            deleted_at__isnull=True
        ).order_by('-created_at')[:50]

        return Response(DebateSessionListSerializer(sessions, many=True).data)


class DebateSessionDetailView(APIView):
    """GET /api/v1/debate/sessions/<uuid:pk>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = DebateSession.objects.get(
                id=pk,
                user=request.user,
                deleted_at__isnull=True
            )
        except DebateSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)

        return Response(DebateSessionDetailSerializer(session).data)

    def delete(self, request, pk):
        """
        NEW: Soft delete session.
        DELETE /api/v1/debate/sessions/<uuid:pk>/
        """
        try:
            session = DebateSession.objects.get(
                id=pk,
                user=request.user,
                deleted_at__isnull=True
            )
        except DebateSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)

        session.deleted_at = timezone.now()
        session.save(update_fields=['deleted_at'])
        return Response(status=204)