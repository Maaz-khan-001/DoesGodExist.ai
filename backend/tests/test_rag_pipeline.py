"""
RAG pipeline integration tests.

Tests the complete flow:
  indexing_app (load document) → indexing_app.tasks (embed) → rag_app (retrieve)

Mocks the embedding service to avoid real model/API calls.
"""

import pytest
from unittest.mock import patch, MagicMock

# Embedding dimension must match VectorField(dimensions=384) in DocumentChunk.
# EMBEDDING_BACKEND=local → LocalEmbeddingService (sentence-transformers, 384-dim).
EMBED_DIM = 384


@pytest.mark.system
@pytest.mark.django_db
class TestIndexingPipeline:

    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_batch_embeddings')
    def test_full_index_and_retrieve_flow(self, mock_embed):
        """
        Tests that after indexing a document and generating embeddings,
        the retrieval service can find relevant chunks.
        """
        from indexing_app.pipeline import IndexingPipeline
        from indexing_app.tasks import embed_chunks
        from rag_app.retrieval_service import RetrievalService

        # FIX 1: Use EMBED_DIM=384 (local backend). Was 1536 (OpenAI).
        mock_embed.return_value = [[0.1 + i * 0.001] * EMBED_DIM for i in range(3)]

        pipeline = IndexingPipeline()
        # FIX 2: ingest_document() has no 'auto_embed' parameter — removed.
        doc = pipeline.ingest_document(
            title='Test Philosophy Document',
            source_type='philosophy',
            chunks_data=[
                {
                    'content': 'Everything that begins to exist has a cause.',
                    'chunk_type': 'philosophy',
                    'stage_tags': ['existence'],
                    'topic_tags': ['kalam', 'causation'],
                    'source_ref': {'title': 'Kalam Cosmological Argument'},
                    'token_count': 10,
                    'is_verified': True,
                },
                {
                    'content': 'The universe began to exist (supported by Big Bang cosmology).',
                    'chunk_type': 'philosophy',
                    'stage_tags': ['existence'],
                    'topic_tags': ['kalam', 'big bang'],
                    'source_ref': {'title': 'Kalam Cosmological Argument'},
                    'token_count': 12,
                    'is_verified': True,
                },
                {
                    'content': 'Therefore, the universe has a cause.',
                    'chunk_type': 'philosophy',
                    'stage_tags': ['existence'],
                    'topic_tags': ['kalam', 'conclusion'],
                    'source_ref': {'title': 'Kalam Cosmological Argument'},
                    'token_count': 8,
                    'is_verified': True,
                },
            ],
        )

        assert doc.indexing_status in ('complete', 'processing')
        assert doc.chunk_count == 3

        # Manually trigger embedding synchronously
        embed_chunks.apply(args=[str(doc.id)])

        doc.refresh_from_db()
        assert doc.indexing_status == 'complete'

        # All chunks should now have embeddings
        from rag_app.models import DocumentChunk
        chunks = DocumentChunk.objects.filter(document=doc)
        assert all(c.embedding is not None for c in chunks)

    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_batch_embeddings')
    def test_idempotent_indexing(self, mock_embed):
        """Running load twice should not create duplicate chunks."""
        from indexing_app.pipeline import IndexingPipeline
        from rag_app.models import DocumentChunk

        mock_embed.return_value = [[0.2] * EMBED_DIM]

        chunk_data = [
            {
                'content': 'Test content',
                'chunk_type': 'philosophy',
                'stage_tags': ['existence'],
                'topic_tags': [],
                'source_ref': {},
                'token_count': 3,
            }
        ]

        pipeline = IndexingPipeline()
        # FIX: ingest_document() has no 'auto_embed' parameter — removed.
        pipeline.ingest_document(
            title='Idempotency Test Doc',
            source_type='philosophy',
            chunks_data=chunk_data,
        )
        pipeline.ingest_document(
            title='Idempotency Test Doc',
            source_type='philosophy',
            chunks_data=chunk_data,
        )

        # Should still be only 1 chunk (get_or_create prevents duplicates)
        count = DocumentChunk.objects.filter(
            document__title='Idempotency Test Doc'
        ).count()
        assert count == 1

    def test_embed_chunks_skips_already_embedded(self):
        """embed_chunks should not re-embed chunks that already have embeddings."""
        from rag_app.models import Document, DocumentChunk
        from indexing_app.tasks import embed_chunks

        doc = Document.objects.create(
            title='Already Embedded',
            source_type='philosophy',
            checksum='already_embedded_001',
            indexing_status='complete',
        )
        # FIX: Use EMBED_DIM=384. Was [0.5]*1536 which caused DataError.
        DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content='Pre-embedded content',
            chunk_type='philosophy',
            stage_tags=['existence'],
            source_ref={},
            token_count=3,
            embedding=[0.5] * EMBED_DIM,
        )

        # FIX: Mock local service (not OpenAI EmbeddingService)
        with patch('rag_app.local_embedding_service.LocalEmbeddingService.get_batch_embeddings') as mock_embed:
            embed_chunks.apply(args=[str(doc.id)])
            # Should NOT call the embedding API since no null embeddings
            mock_embed.assert_not_called()


@pytest.mark.system
@pytest.mark.django_db
class TestRetrievalCaching:

    # FIX: EMBEDDING_BACKEND=local → get_embedding_service() returns LocalEmbeddingService.
    # Patching EmbeddingService.get_embedding has no effect — must patch LocalEmbeddingService.

    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_embedding')
    def test_retrieval_cache_hit_on_second_call(self, mock_embed):
        """Second identical query should use cache, not re-embed.

        FIX: The cache stores chunk IDs (a list). On cache hit, the code
        checks `if chunks:` — if no DB chunks exist, the list is empty and
        it falls through to call get_embedding again (2 calls, not 1).
        Solution: create a real verified chunk so the cache hit path returns it.
        """
        from rag_app.retrieval_service import RetrievalService
        from rag_app.models import Document, DocumentChunk
        from django.core.cache import cache
        cache.clear()

        mock_embed.return_value = [0.1] * EMBED_DIM

        # Create a real chunk so the cache stores a non-empty ID list
        doc, _ = Document.objects.get_or_create(
            checksum='cache_hit_test_doc',
            defaults={'title': 'Cache Test', 'source_type': 'philosophy',
                      'indexing_status': 'complete'}
        )
        DocumentChunk.objects.create(
            document=doc, chunk_index=0,
            content='God exists', chunk_type='philosophy',
            stage_tags=['existence'], topic_tags=[], source_ref={},
            token_count=5, is_verified=True,
            embedding=[0.1] * EMBED_DIM,
        )

        svc = RetrievalService()
        svc.retrieve('does god exist', stage='existence')
        svc.retrieve('does god exist', stage='existence')

        # get_embedding called only once (second call hits cache with real chunk IDs)
        assert mock_embed.call_count == 1


    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_embedding')
    def test_different_stages_cached_separately(self, mock_embed):
        """Queries for different stages should not share cache."""
        from rag_app.retrieval_service import RetrievalService
        from django.core.cache import cache
        cache.clear()

        mock_embed.return_value = [0.1] * EMBED_DIM

        svc = RetrievalService()
        svc.retrieve('does god exist', stage='existence')
        svc.retrieve('does god exist', stage='prophethood')

        # Two different cache keys → two embedding calls
        assert mock_embed.call_count == 2