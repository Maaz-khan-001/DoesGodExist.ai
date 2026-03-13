import logging
from config.celery import app
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@app.task
def reset_daily_turns():
    """Resets daily turn counts for all users at midnight UTC."""
    from debate_app.models import User
    today = timezone.now().date()
    updated = User.objects.exclude(daily_reset_date=today).update(
        daily_turn_count=0,
        daily_reset_date=today,
    )
    logger.info(f'Daily turn reset: {updated} users reset')
    return updated


@app.task
def generate_session_title(session_id: str, first_user_message: str):
    """
    Uses GPT-4o-mini to generate a short title for a debate session.
    Called after the first exchange so the session has context.
    """
    import os
    from openai import OpenAI
    from debate_app.models import DebateSession

    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=20,
            temperature=0.5,
            messages=[{
                'role': 'user',
                'content': (
                    f'Generate a concise 4-5 word title for a philosophical debate '
                    f'that started with this question: "{first_user_message[:150]}"\n'
                    f'Reply with ONLY the title. No quotes, no punctuation at end.'
                )
            }]
        )
        title = response.choices[0].message.content.strip()[:200]

        DebateSession.objects.filter(pk=session_id).update(title=title)
        logger.info(f'Session title generated: "{title}" for {session_id}')
        return title

    except Exception as e:
        logger.error(f'generate_session_title failed for {session_id}: {e}')
        # Don't raise — this is a non-critical task


@app.task
def cleanup_anonymous_sessions():
    """
    Removes anonymous users inactive for 30+ days.
    Runs weekly (Sunday 2am UTC).
    """
    from debate_app.models import User
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    old_anon_users = User.objects.filter(
        is_anonymous_user=True,
        last_active_at__lt=cutoff,
    )
    count = old_anon_users.count()

    # Sessions are CASCADE deleted when user is deleted
    old_anon_users.delete()
    logger.info(f'Cleaned up {count} inactive anonymous users')
    return count
