"""
debate_app/serializers_user.py

Referenced by settings.py → REST_AUTH → USER_DETAILS_SERIALIZER
                                      → REGISTER_SERIALIZER
                                      → TOKEN_SERIALIZER

If this file is absent or the classes are missing, dj-rest-auth crashes on
every auth endpoint with an ImportError or AttributeError at startup.
"""
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import TokenSerializer
from .models import User


class UserSerializer(serializers.ModelSerializer):
    daily_turns_remaining = serializers.SerializerMethodField()

    def get_daily_turns_remaining(self, obj):
        from debate_app.views import DAILY_TURN_LIMITS
        from django.utils import timezone
        today = timezone.now().date()
        if obj.daily_reset_date != today:
            return DAILY_TURN_LIMITS.get(obj.tier, 5)
        limit = DAILY_TURN_LIMITS.get(obj.tier, 5)
        return max(0, limit - obj.daily_turn_count)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'tier', 'preferred_language',
            'is_anonymous_user', 'daily_turns_remaining', 'created_at',
        ]
        read_only_fields = fields


class TokenWithUserSerializer(TokenSerializer):
    """
    FIX: dj-rest-auth's default TokenSerializer only returns {'key': '...'}.
    The test (and frontend) expect {'key': '...', 'user': {...}}.
    Extend it to include the full user object alongside the token.

    Registered in settings.py → REST_AUTH → TOKEN_SERIALIZER.

    NOTE: Do NOT pass source='user' — DRF raises an error when source
    matches the field name exactly. The Token model has a 'user' FK,
    so DRF resolves it automatically from the field name alone.
    """
    user = UserSerializer(read_only=True)

    class Meta(TokenSerializer.Meta):
        fields = TokenSerializer.Meta.fields + ('user',)



class UserRegistrationSerializer(RegisterSerializer):
    """
    Extends dj-rest-auth's built-in RegisterSerializer.

    dj-rest-auth's default RegisterSerializer expects a 'username' field.
    Because our User model has no username (USERNAME_FIELD = 'email'),
    we override to remove username and only require email + password.

    The parent class already handles password1/password2 validation and
    calls allauth's registration pipeline, so we just need to remove
    the username field and ensure email is the identifier.
    """
    # Remove username field entirely (parent class adds it by default)
    username = None

    # email is already on the parent; re-declare to make it explicitly required
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        """
        FIX: allauth with EMAIL_VERIFICATION='optional' hits the DB UNIQUE
        constraint before returning a 400, causing IntegrityError instead.
        Validate uniqueness here explicitly so a clean 400 is returned.
        """
        email = email.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'A user with this email address already exists.'
            )
        return email

    def get_cleaned_data(self):
        """
        Called by allauth's save() to extract data for user creation.
        Must return at minimum email + password fields.
        """
        data = super().get_cleaned_data()
        # Remove username key if parent inserted it — avoids passing
        # an unexpected kwarg to our custom UserManager.create_user()
        data.pop('username', None)
        return data

    def save(self, request):
        """
        Creates the user and sets their tier to 'registered' immediately,
        rather than leaving them at the default 'anonymous' tier.
        """
        user = super().save(request)
        user.tier = 'registered'
        user.is_anonymous_user = False
        user.save(update_fields=['tier', 'is_anonymous_user'])
        return user