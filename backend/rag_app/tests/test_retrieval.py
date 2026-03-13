
#============ for open ai ==================

# import pytest
# from unittest.mock import patch, MagicMock
# from django.core.cache import cache
# 
# 
# @pytest.mark.django_db
# class TestEmbeddingService:
# 
#     def setup_method(self):
#         cache.clear()
# 
#     @patch('openai.resources.embeddings.Embeddings.create')
#     def test_get_embedding_returns_list_of_floats(self, mock_create):
#         from rag_app.embedding_service import EmbeddingService
#         fake_embedding = [0.1] * 1536
#         mock_resp = MagicMock()
#         mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
#         mock_create.return_value = mock_resp
# 
#         svc = EmbeddingService()
#         result = svc.get_embedding('test text')
#         assert isinstance(result, list)
#         assert len(result) == 1536
#         assert all(isinstance(x, float) for x in result)
# 
#     @patch('openai.resources.embeddings.Embeddings.create')
#     def test_get_embedding_returns_correct_length(self, mock_create):
#         # Dimension validation happens in embed_chunks task, not get_embedding.
#         # get_embedding simply returns whatever the API sends back.
#         from rag_app.embedding_service import EmbeddingService
#         fake_embedding = [0.1] * 1536
#         mock_resp = MagicMock()
#         mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
#         mock_create.return_value = mock_resp
# 
#         svc = EmbeddingService()
#         result = svc.get_embedding('test text')
#         assert len(result) == 1536
# 
#     @patch('openai.resources.embeddings.Embeddings.create')
#     def test_embedding_is_cached_after_first_call(self, mock_create):
#         from rag_app.embedding_service import EmbeddingService
#         fake_embedding = [0.1] * 1536
#         mock_resp = MagicMock()
#         mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
#         mock_create.return_value = mock_resp
# 
#         svc = EmbeddingService()
#         text = 'unique test text for caching xyz123'
#         svc.get_embedding(text)
#         svc.get_embedding(text)  # second call — should use cache
# 
#         # API should only be called once
#         assert mock_create.call_count == 1
# 
# 
# @pytest.mark.django_db
# class TestRetrievalService:
# 
#     def _make_chunk(self, stage='existence', content='God exists', checksum='ret_test_001',
#                     index=0, is_verified=True):
#         from rag_app.models import Document, DocumentChunk
#         doc, _ = Document.objects.get_or_create(
#             checksum=checksum,
#             defaults={
#                 'title': 'Test Document',
#                 'source_type': 'philosophy',
#                 'indexing_status': 'complete',
#             }
#         )
#         return DocumentChunk.objects.create(
#             document=doc,
#             chunk_index=index,
#             content=content,
#             chunk_type='philosophy',
#             stage_tags=[stage],
#             topic_tags=['test'],
#             source_ref={},
#             token_count=10,
#             is_verified=is_verified,
#             embedding=[0.1] * 1536,
#         )
# 
#     def setup_method(self):
#         cache.clear()
# 
#     @patch('rag_app.retrieval_service.RetrievalService.retrieve')
#     def test_retrieve_returns_chunks(self, mock_retrieve):
#         from rag_app.retrieval_service import RetrievalService
#         mock_chunk = MagicMock()
#         mock_chunk.content = 'God exists because...'
#         mock_retrieve.return_value = [mock_chunk]
# 
#         svc = RetrievalService()
#         results = svc.retrieve('Does God exist?', stage='existence')
#         assert len(results) == 1
# 
#     @patch('rag_app.embedding_service.EmbeddingService.get_embedding')
#     def test_retrieve_returns_empty_when_no_verified_chunks(self, mock_embed):
#         from rag_app.retrieval_service import RetrievalService
#         mock_embed.return_value = [0.1] * 1536
# 
#         # Only unverified chunk exists
#         self._make_chunk(checksum='unverified_001', is_verified=False)
# 
#         svc = RetrievalService()
#         results = svc.retrieve('Does God exist?', stage='existence')
#         assert results == []
# 
#     @patch('rag_app.embedding_service.EmbeddingService.get_embedding')
#     def test_token_budget_limits_returned_chunks(self, mock_embed):
#         from rag_app.retrieval_service import RetrievalService
#         from rag_app.models import Document, DocumentChunk
#         mock_embed.return_value = [0.1] * 1536
# 
#         doc, _ = Document.objects.get_or_create(
#             checksum='budget_test_doc',
#             defaults={
#                 'title': 'Budget Test',
#                 'source_type': 'philosophy',
#                 'indexing_status': 'complete',
#             }
#         )
#         for i in range(5):
#             DocumentChunk.objects.create(
#                 document=doc,
#                 chunk_index=i + 10,
#                 content='A ' * 300,
#                 chunk_type='philosophy',
#                 stage_tags=['existence'],
#                 source_ref={},
#                 token_count=600,
#                 is_verified=True,
#                 embedding=[0.1] * 1536,
#             )
# 
#         svc = RetrievalService()
#         results = svc.retrieve('test', stage='existence', token_budget=1500)
#         total_tokens = sum(c.token_count for c in results)
#         assert total_tokens <= 1500
# 
# 
# @pytest.mark.django_db
# class TestEmbedChunksTask:
# 
#     @patch('rag_app.embedding_service.EmbeddingService.get_batch_embeddings')
#     def test_embed_chunks_fills_null_embeddings(self, mock_embed):
#         from rag_app.models import Document, DocumentChunk
#         from indexing_app.tasks import embed_chunks
#         mock_embed.return_value = [[0.1] * 1536]
# 
#         doc = Document.objects.create(
#             title='Test Doc',
#             source_type='philosophy',
#             checksum='embed_test_001',
#             indexing_status='processing',
#         )
#         chunk = DocumentChunk.objects.create(
#             document=doc,
#             chunk_index=0,
#             content='Test content',
#             chunk_type='philosophy',
#             stage_tags=['existence'],
#             source_ref={},
#             token_count=5,
#             embedding=None,
#         )
# 
#         embed_chunks(str(doc.id))
# 
#         chunk.refresh_from_db()
#         assert chunk.embedding is not None
# 
#         doc.refresh_from_db()
#         assert doc.indexing_status == 'complete'
# 
#     @patch('rag_app.embedding_service.EmbeddingService.get_batch_embeddings')
#     def test_embed_chunks_marks_failed_on_dimension_mismatch(self, mock_embed):
#         from rag_app.models import Document, DocumentChunk
#         from indexing_app.tasks import embed_chunks
#         mock_embed.return_value = [[0.1] * 384]  # wrong dimension
# 
#         doc = Document.objects.create(
#             title='Wrong Dim Doc',
#             source_type='philosophy',
#             checksum='embed_test_002',
#             indexing_status='processing',
#         )
#         DocumentChunk.objects.create(
#             document=doc,
#             chunk_index=0,
#             content='Test',
#             chunk_type='philosophy',
#             stage_tags=['existence'],
#             source_ref={},
#             token_count=2,
#             embedding=None,
#         )
# 
#         with pytest.raises(ValueError):
#             embed_chunks(str(doc.id))
# 
#         doc.refresh_from_db()
#         assert doc.indexing_status == 'failed'





#-========================== for local 384 ===============
import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache


@pytest.mark.django_db
class TestEmbeddingService:

    def setup_method(self):
        cache.clear()

    @patch('openai.resources.embeddings.Embeddings.create')
    def test_get_embedding_returns_list_of_floats(self, mock_create):
        from rag_app.embedding_service import EmbeddingService
        fake_embedding = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
        mock_create.return_value = mock_resp

        svc = EmbeddingService()
        result = svc.get_embedding('test text')
        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)

    @patch('openai.resources.embeddings.Embeddings.create')
    def test_get_embedding_returns_correct_length(self, mock_create):
        # Dimension validation happens in embed_chunks task, not get_embedding.
        # get_embedding simply returns whatever the API sends back.
        from rag_app.embedding_service import EmbeddingService
        fake_embedding = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
        mock_create.return_value = mock_resp

        svc = EmbeddingService()
        result = svc.get_embedding('test text')
        assert len(result) == 1536

    @patch('openai.resources.embeddings.Embeddings.create')
    def test_embedding_is_cached_after_first_call(self, mock_create):
        from rag_app.embedding_service import EmbeddingService
        fake_embedding = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(embedding=fake_embedding, index=0)]
        mock_create.return_value = mock_resp

        svc = EmbeddingService()
        text = 'unique test text for caching xyz123'
        svc.get_embedding(text)
        svc.get_embedding(text)  # second call — should use cache

        # API should only be called once
        assert mock_create.call_count == 1


@pytest.mark.django_db
class TestRetrievalService:

    # FIX: DB VectorField is dimensions=384 (local/sentence-transformers).
    # Was [0.1] * 1536 which matched OpenAI — caused DataError in test DB.
    EMBED_DIM = 384

    def _make_chunk(self, stage='existence', content='God exists', checksum='ret_test_001',
                    index=0, is_verified=True):
        from rag_app.models import Document, DocumentChunk
        doc, _ = Document.objects.get_or_create(
            checksum=checksum,
            defaults={
                'title': 'Test Document',
                'source_type': 'philosophy',
                'indexing_status': 'complete',
            }
        )
        return DocumentChunk.objects.create(
            document=doc,
            chunk_index=index,
            content=content,
            chunk_type='philosophy',
            stage_tags=[stage],
            topic_tags=['test'],
            source_ref={},
            token_count=10,
            is_verified=is_verified,
            embedding=[0.1] * self.EMBED_DIM,   # FIX: was 1536
        )

    def setup_method(self):
        cache.clear()

    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_retrieve_returns_chunks(self, mock_retrieve):
        from rag_app.retrieval_service import RetrievalService
        mock_chunk = MagicMock()
        mock_chunk.content = 'God exists because...'
        mock_retrieve.return_value = [mock_chunk]

        svc = RetrievalService()
        results = svc.retrieve('Does God exist?', stage='existence')
        assert len(results) == 1

    @patch('rag_app.embedding_service.EmbeddingService.get_embedding')
    def test_retrieve_returns_empty_when_no_verified_chunks(self, mock_embed):
        from rag_app.retrieval_service import RetrievalService
        mock_embed.return_value = [0.1] * self.EMBED_DIM   # FIX: was 1536

        # Only unverified chunk exists
        self._make_chunk(checksum='unverified_001', is_verified=False)

        svc = RetrievalService()
        results = svc.retrieve('Does God exist?', stage='existence')
        assert results == []

    @patch('rag_app.embedding_service.EmbeddingService.get_embedding')
    def test_token_budget_limits_returned_chunks(self, mock_embed):
        from rag_app.retrieval_service import RetrievalService
        from rag_app.models import Document, DocumentChunk
        mock_embed.return_value = [0.1] * self.EMBED_DIM   # FIX: was 1536

        doc, _ = Document.objects.get_or_create(
            checksum='budget_test_doc',
            defaults={
                'title': 'Budget Test',
                'source_type': 'philosophy',
                'indexing_status': 'complete',
            }
        )
        for i in range(5):
            DocumentChunk.objects.create(
                document=doc,
                chunk_index=i + 10,
                content='A ' * 300,
                chunk_type='philosophy',
                stage_tags=['existence'],
                source_ref={},
                token_count=600,
                is_verified=True,
                embedding=[0.1] * self.EMBED_DIM,   # FIX: was 1536
            )

        svc = RetrievalService()
        results = svc.retrieve('test', stage='existence', token_budget=1500)
        total_tokens = sum(c.token_count for c in results)
        assert total_tokens <= 1500


@pytest.mark.django_db
class TestEmbedChunksTask:

    # FIX 1: EMBEDDING_BACKEND=local means get_embedding_service() returns
    # LocalEmbeddingService, not EmbeddingService. Mock the correct class.
    #
    # FIX 2: embed_chunks is a Celery task with bind=True. Calling
    # embed_chunks(doc_id) directly skips the function body entirely because
    # Celery intercepts it and 'self' (the task instance) is missing.
    # Use embed_chunks.apply(args=[doc_id]) which runs synchronously and
    # correctly passes self.

    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_batch_embeddings')
    def test_embed_chunks_fills_null_embeddings(self, mock_embed):
        from rag_app.models import Document, DocumentChunk
        from indexing_app.tasks import embed_chunks
        mock_embed.return_value = [[0.1] * 384]

        doc = Document.objects.create(
            title='Test Doc',
            source_type='philosophy',
            checksum='embed_test_001',
            indexing_status='processing',
        )
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content='Test content',
            chunk_type='philosophy',
            stage_tags=['existence'],
            source_ref={},
            token_count=5,
            embedding=None,
        )

        embed_chunks.apply(args=[str(doc.id)])

        chunk.refresh_from_db()
        assert chunk.embedding is not None

        doc.refresh_from_db()
        assert doc.indexing_status == 'complete'

    @patch('rag_app.local_embedding_service.LocalEmbeddingService.get_batch_embeddings')
    def test_embed_chunks_marks_failed_on_dimension_mismatch(self, mock_embed):
        from rag_app.models import Document, DocumentChunk
        from indexing_app.tasks import embed_chunks

        # Return wrong dimension (999) to trigger ValueError in tasks.py
        # (expected_dim = 384, so 999 != 384 raises ValueError)
        mock_embed.return_value = [[0.1] * 999]

        doc = Document.objects.create(
            title='Wrong Dim Doc',
            source_type='philosophy',
            checksum='embed_test_002',
            indexing_status='processing',
        )
        DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content='Test',
            chunk_type='philosophy',
            stage_tags=['existence'],
            source_ref={},
            token_count=2,
            embedding=None,
        )

        # .apply() raises the exception directly (no Celery retry machinery)
        with pytest.raises(ValueError):
            embed_chunks.apply(args=[str(doc.id)], throw=True)

        doc.refresh_from_db()
        assert doc.indexing_status == 'failed'