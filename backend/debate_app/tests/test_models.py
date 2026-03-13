import pytest
from django.db import IntegrityError
from django.utils import timezone
from debate_app.tests.factories import (
    UserFactory, AnonymousUserFactory, DebateSessionFactory,
    UserMessageFactory, AssistantMessageFactory
)


@pytest.mark.django_db
class TestUserModel:

    def test_user_str_with_email(self):
        user = UserFactory(email='test@example.com')
        assert str(user) == 'test@example.com'

    def test_anonymous_user_str(self):
        user = AnonymousUserFactory(session_key='abc123')
        assert str(user) == 'anon:abc123'

    def test_user_default_tier_is_anonymous(self):
        user = AnonymousUserFactory()
        assert user.tier == 'anonymous'

    def test_registered_user_tier(self):
        user = UserFactory()
        assert user.tier == 'registered'

    def test_user_uuid_primary_key(self):
        user = UserFactory()
        assert user.id is not None
        assert len(str(user.id)) == 36  # UUID format


@pytest.mark.django_db
class TestDebateSessionModel:

    def test_session_default_stage_is_existence(self):
        session = DebateSessionFactory()
        assert session.current_stage == 'existence'

    def test_session_str_representation(self):
        session = DebateSessionFactory()
        result = str(session)
        assert 'existence' in result

    def test_session_title_is_nullable(self):
        session = DebateSessionFactory()
        assert session.title is None

    def test_session_total_turns_starts_at_zero(self):
        session = DebateSessionFactory()
        assert session.total_turns == 0

    def test_session_soft_delete(self):
        session = DebateSessionFactory()
        assert session.deleted_at is None
        session.deleted_at = timezone.now()
        session.save()
        # Still exists in DB
        from debate_app.models import DebateSession
        assert DebateSession.objects.filter(pk=session.pk).exists()
        # But filtered out by deleted_at__isnull=True queries
        assert not DebateSession.objects.filter(
            pk=session.pk, deleted_at__isnull=True
        ).exists()


@pytest.mark.django_db
class TestMessageModel:

    def test_message_sequence_unique_within_session(self):
        session = DebateSessionFactory()
        UserMessageFactory(session=session, sequence_num=0)
        with pytest.raises(IntegrityError):
            UserMessageFactory(session=session, sequence_num=0)

    def test_same_sequence_num_allowed_in_different_sessions(self):
        session1 = DebateSessionFactory()
        session2 = DebateSessionFactory()
        msg1 = UserMessageFactory(session=session1, sequence_num=0)
        msg2 = UserMessageFactory(session=session2, sequence_num=0)
        assert msg1.id != msg2.id

    def test_message_ordering_by_sequence_num(self):
        session = DebateSessionFactory()
        UserMessageFactory(session=session, sequence_num=0)
        AssistantMessageFactory(session=session, sequence_num=1)
        UserMessageFactory(session=session, sequence_num=2)

        msgs = list(session.messages.all())
        assert [m.sequence_num for m in msgs] == [0, 1, 2]

    def test_message_citations_default_empty_list(self):
        session = DebateSessionFactory()
        msg = UserMessageFactory(session=session, sequence_num=0, citations=[])
        assert msg.citations == []

    def test_assistant_message_with_citations(self):
        session = DebateSessionFactory()
        msg = AssistantMessageFactory(session=session, sequence_num=1)
        assert len(msg.citations) > 0
        assert 'source_type' in msg.citations[0]
        assert 'reference' in msg.citations[0]
