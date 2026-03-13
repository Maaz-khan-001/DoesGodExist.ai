from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, DebateSession, Message, PromptTemplate


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'tier', 'is_anonymous_user', 'daily_turn_count',
                    'created_at', 'last_active_at')
    list_filter = ('tier', 'is_anonymous_user', 'is_staff', 'is_active')
    search_fields = ('email', 'session_key')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'last_active_at')

    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Profile', {'fields': ('tier', 'preferred_language', 'is_anonymous_user',
                                'session_key')}),
        ('Usage', {'fields': ('daily_turn_count', 'daily_reset_date')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'last_active_at', 'deleted_at')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2', 'tier')}),
    )


@admin.register(DebateSession)
class DebateSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'current_stage', 'debate_mode',
                    'detected_persona', 'total_turns', 'total_cost_usd', 'created_at')
    list_filter = ('current_stage', 'debate_mode', 'detected_persona')
    search_fields = ('user__email', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_cost_usd', 'total_tokens')
    ordering = ('-created_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # FIX: Added 'content_preview' so assertContains(response, 'Test message') passes.
    # 'content' itself can't be in list_display (TextField) — use a short_description method.
    list_display = ('id', 'session', 'role', 'stage', 'sequence_num',
                    'content_preview', 'token_count', 'created_at')
    list_filter = ('role', 'stage')
    search_fields = ('session__user__email', 'content')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:80] if obj.content else ''


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('stage', 'version', 'is_active', 'tone', 'created_at')
    list_filter = ('stage', 'is_active', 'tone')
    ordering = ('stage', '-version')