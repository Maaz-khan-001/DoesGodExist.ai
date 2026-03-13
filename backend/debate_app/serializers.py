from rest_framework import serializers
from .models import Message, DebateSession


class DebateMessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, min_length=1)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    language = serializers.ChoiceField(
        choices=['en', 'ar', 'ur'],
        default='en'
    )
    debate_mode = serializers.ChoiceField(
        choices=['standard', 'scientific', 'philosophical', 'reflective',
                 'comparative', 'prophethood_mode'],
        required=False,
        default='standard'
    )

    def validate_message(self, value):
        """
        Guard against basic prompt injection attempts.
        """
        injection_patterns = [
            'ignore previous instructions',
            'disregard your training',
            'forget everything above',
            'new instructions:',
            'system prompt:',
            'you are now a',
            'act as if you are',
            'pretend you have no',
        ]
        lower = value.lower()
        for pattern in injection_patterns:
            if pattern in lower:
                raise serializers.ValidationError(
                    'Message contains disallowed content. Please rephrase.'
                )
        return value.strip()


class CitationSerializer(serializers.Serializer):
    """Serializes a citation dict stored in Message.citations JSON field."""
    source_type = serializers.CharField()
    reference = serializers.CharField()
    content = serializers.CharField()
    is_verified = serializers.BooleanField(default=False)


class MessageOutputSerializer(serializers.ModelSerializer):
    citations = CitationSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'stage', 'citations',
                  'sequence_num', 'created_at']


class DebateSessionListSerializer(serializers.ModelSerializer):
    """
    For GET /sessions/ — excludes messages for performance.
    Adds computed daily_turns_remaining.
    """
    # FIX: Use title field (now exists on model)
    title = serializers.CharField(allow_null=True, read_only=True)

    class Meta:
        model = DebateSession
        fields = [
            'id', 'title', 'current_stage', 'debate_mode', 'detected_persona',
            'god_acceptance', 'prophecy_acceptance', 'muhammad_acceptance',
            'total_turns', 'created_at', 'updated_at',
        ]


class DebateSessionDetailSerializer(serializers.ModelSerializer):
    """For GET /sessions/<id>/ — includes full message history."""
    messages = MessageOutputSerializer(many=True, read_only=True)
    title = serializers.CharField(allow_null=True, read_only=True)

    class Meta:
        model = DebateSession
        fields = [
            'id', 'title', 'current_stage', 'debate_mode', 'detected_persona',
            'god_acceptance', 'prophecy_acceptance', 'muhammad_acceptance',
            'total_turns', 'created_at', 'updated_at', 'messages',
        ]
