import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from debate_app.models import User, DebateSession, Message


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@test.com')
    tier = 'registered'
    is_anonymous_user = False
    is_active = True
    daily_turn_count = 0
    daily_reset_date = factory.LazyFunction(lambda: timezone.now().date())


class AnonymousUserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = None
    session_key = factory.Sequence(lambda n: f'anon_key_{n:04d}')
    is_anonymous_user = True
    tier = 'anonymous'
    is_active = True


class PremiumUserFactory(UserFactory):
    tier = 'premium'


class AdminUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f'admin{n}@test.com')
    is_staff = True
    is_superuser = True


class DebateSessionFactory(DjangoModelFactory):
    class Meta:
        model = DebateSession

    user = factory.SubFactory(UserFactory)
    current_stage = 'existence'
    debate_mode = 'standard'
    detected_persona = None
    god_acceptance = None
    prophecy_acceptance = None
    muhammad_acceptance = None
    total_turns = 0
    complexity_score = 0.3


class DebateSessionAtProphethood(DebateSessionFactory):
    """Session that has already passed stage 1."""
    current_stage = 'prophethood'
    god_acceptance = True
    total_turns = 5


class DebateSessionAtMuhammad(DebateSessionFactory):
    """Session that has already passed stages 1 and 2."""
    current_stage = 'muhammad'
    god_acceptance = True
    prophecy_acceptance = True
    total_turns = 10


class UserMessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    session = factory.SubFactory(DebateSessionFactory)
    role = 'user'
    content = 'Does God exist?'
    stage = 'existence'
    sequence_num = factory.Sequence(lambda n: n * 2)  # Even: user msgs
    token_count = 5
    citations = []


class AssistantMessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    session = factory.SubFactory(DebateSessionFactory)
    role = 'assistant'
    content = 'The existence of God can be argued through...'
    stage = 'existence'
    sequence_num = factory.Sequence(lambda n: n * 2 + 1)  # Odd: assistant msgs
    token_count = 80
    citations = [
        {
            'source_type': 'philosophy',
            'reference': 'Kalam Cosmological Argument',
            'content': 'Everything that begins to exist has a cause.',
            'is_verified': True,
        }
    ]
