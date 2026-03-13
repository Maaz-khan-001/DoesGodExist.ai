from django.contrib import admin
from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source_type', 'author', 'indexing_status', 'chunk_count', 'created_at')
    list_filter = ('source_type', 'indexing_status', 'created_at')
    search_fields = ('title', 'author', 'checksum')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'checksum', 'chunk_count')

    fieldsets = (
        (None, {'fields': ('id', 'title', 'source_type')}),
        ('Source Info', {'fields': ('author', 'checksum')}),
        ('Status', {'fields': ('indexing_status', 'chunk_count')}),
        ('Timestamps', {'fields': ('created_at', 'deleted_at')}),
        ('Metadata', {'fields': ('metadata',)}),
    )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    # FIX: Added 'content_preview' so assertContains(response, 'Test content') passes.
    # TextField can't go directly in list_display — use a short_description method.
    list_display = ('id', 'document', 'chunk_index', 'chunk_type',
                    'content_preview', 'token_count', 'is_verified', 'embedding_model', 'created_at')
    list_filter = ('chunk_type', 'is_verified', 'embedding_model', 'created_at')
    search_fields = ('document__title', 'content', 'content_arabic', 'content_urdu')
    ordering = ('document', 'chunk_index')
    readonly_fields = ('id', 'created_at', 'embedding', 'token_count')

    fieldsets = (
        (None, {'fields': ('id', 'document', 'chunk_index')}),
        ('Content', {'fields': ('content', 'content_arabic', 'content_urdu')}),
        ('Classification', {'fields': ('chunk_type', 'stage_tags', 'topic_tags')}),
        ('Embedding', {'fields': ('embedding', 'embedding_model', 'embedding_version')}),
        ('Status', {'fields': ('is_verified', 'token_count')}),
        ('Source', {'fields': ('source_ref',)}),
        ('Timestamps', {'fields': ('created_at', 'deleted_at')}),
    )

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:80] if obj.content else ''

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:
            readonly.extend(['document'])
        return readonly