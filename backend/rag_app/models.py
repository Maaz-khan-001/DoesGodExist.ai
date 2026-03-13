from django.db import models
from uuid import uuid4
from pgvector.django import VectorField
from django.contrib.postgres.fields import ArrayField


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=512)
    source_type = models.CharField(
        max_length=30,
        choices=[
            ('quran',                 'Quran'),
            ('hadith',                'Hadith'),
            ('philosophy',            'Philosophy / Rational Arguments'),
            ('scientific',            'Scientific Signs'),
            ('comparative_religion',  'Comparative Religion'),
            ('logic',                 'Logic / Reasoning Framework'),
            ('meta',                  'Meta / Debate Topics / Glossary'),
        ]
    )
    author = models.CharField(max_length=256, null=True, blank=True)
    checksum = models.CharField(max_length=64, unique=True)
    indexing_status = models.CharField(max_length=20,
        choices=[('pending','Pending'),('processing','Processing'),
                 ('complete','Complete'),('failed','Failed')],
        default='pending')
    chunk_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    content_arabic = models.TextField(null=True, blank=True)
    # Urdu stored for Quran only - from verified source, NOT auto-translated
    content_urdu = models.TextField(null=True, blank=True)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    token_count = models.IntegerField()
    chunk_type = models.CharField(max_length=30)
    stage_tags = ArrayField(models.CharField(max_length=50), default=list)
    topic_tags = ArrayField(models.CharField(max_length=50), default=list)
    source_ref = models.JSONField(default=dict)
    embedding_model = models.CharField(max_length=64, default='text-embedding-3-small')
    embedding_version = models.IntegerField(default=1)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    embedding_dim = models.IntegerField(null=True, blank=True)  

    class Meta:
        indexes = [
            models.Index(fields=['chunk_type','embedding_version']),
            models.Index(fields=['is_verified','deleted_at']),
        ]
        ordering = ['chunk_index']

    def __str__(self):
        return f'{self.chunk_type}:{self.chunk_index}'
