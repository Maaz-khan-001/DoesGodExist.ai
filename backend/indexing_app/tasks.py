import logging
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def embed_chunks(self, document_id: str, batch_size: int = 100):
    """
    Generate embeddings for all unembedded chunks of a document.

    Called automatically by IndexingPipeline after document ingestion.
    Safe to call multiple times — skips already-embedded chunks.

    Can also be called manually:
      python manage.py generate_embeddings --document-id <uuid>
      python manage.py generate_embeddings --sync   (skip Celery)

    Retry:
      Retries up to 3 times with 60s delay on transient failures.
      Does NOT retry on ValueError (dimension mismatch) — that is a
      config error requiring manual intervention.

    Args:
      document_id: UUID string of the Document to embed
      batch_size:  Number of chunks per OpenAI API call (max 2048)

    Returns:
      int: Number of chunks embedded, or 0 if nothing to embed
    """
    from rag_app.models import Document, DocumentChunk
    from rag_app.embedding_service import get_embedding_service, get_expected_dimension

    # Load document
    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error(f'embed_chunks: Document {document_id} not found — skipping')
        return 0

    # Find all chunks without embeddings
    chunks = list(
        DocumentChunk.objects
        .filter(document=doc, embedding__isnull=True)
        .order_by('chunk_index')
    )

    if not chunks:
        logger.info(
            f'embed_chunks: No unembedded chunks for "{doc.title}". '
            f'Marking document as complete.'
        )
        doc.indexing_status = 'complete'
        doc.save(update_fields=['indexing_status'])
        return 0

    logger.info(
        f'embed_chunks: Starting for "{doc.title}" — '
        f'{len(chunks)} chunks to embed'
    )

    try:
        emb_svc = get_embedding_service()
        expected_dim = get_expected_dimension()
        total_embedded = 0

        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start:batch_start + batch_size]
            texts = [c.content for c in batch]

            logger.info(
                f'  Batch {batch_start // batch_size + 1} / '
                f'{(len(chunks) + batch_size - 1) // batch_size}: '
                f'{len(batch)} chunks'
            )

            embeddings = emb_svc.get_batch_embeddings(texts)

            if not embeddings:
                raise RuntimeError(
                    f'Embedding service returned empty list for batch starting at {batch_start}'
                )

            # SAFETY: validate dimension matches VectorField
            actual_dim = len(embeddings[0])
            if actual_dim != expected_dim:
                raise ValueError(
                    f'Embedding dimension mismatch: '
                    f'got {actual_dim}, expected {expected_dim}. '
                    f'Set EMBEDDING_BACKEND=openai to use {expected_dim}-dim embeddings, '
                    f'or change VectorField(dimensions={actual_dim}) in DocumentChunk model '
                    f'and re-run migrations.'
                )

            # Assign embeddings to chunk objects
            for chunk, emb in zip(batch, embeddings):
                chunk.embedding = emb
                chunk.embedding_dim = len(emb)

            # Bulk update — much faster than individual saves
            DocumentChunk.objects.bulk_update(
                batch,
                fields=['embedding', 'embedding_dim'],
                batch_size=50,
            )
            total_embedded += len(batch)
            logger.info(f'  → {total_embedded}/{len(chunks)} embedded so far')

        # Mark document as complete
        doc.indexing_status = 'complete'
        doc.save(update_fields=['indexing_status'])

        logger.info(
            f'embed_chunks: COMPLETE for "{doc.title}". '
            f'{total_embedded} chunks embedded.'
        )
        return total_embedded

    except ValueError as e:
        # Dimension mismatch — config error, don't retry
        logger.error(f'embed_chunks FATAL (will not retry): {e}')
        doc.indexing_status = 'failed'
        doc.metadata = {**doc.metadata, 'embed_error': str(e)}
        doc.save(update_fields=['indexing_status', 'metadata'])
        raise  # Raise without retry

    except Exception as exc:
        logger.error(
            f'embed_chunks FAILED for "{doc.title}": {exc}',
            exc_info=True,
        )
        doc.indexing_status = 'failed'
        doc.save(update_fields=['indexing_status'])
        # Celery will retry (up to max_retries=3, delay=60s)
        raise self.retry(exc=exc)


@app.task
def re_embed_all(force: bool = False):
    """
    Admin task: Re-embed ALL document chunks from scratch.

    Use when:
      - Switching from local embeddings (384-dim) to OpenAI (1536-dim)
      - Upgrading the embedding model
      - Fixing corrupt embeddings

    WARNING:
      - Clears all existing embeddings first
      - Will take several minutes for large knowledge bases
      - Ensure the embedding dimension matches VectorField before running

    Usage (from Django shell or Celery):
      from indexing_app.tasks import re_embed_all
      re_embed_all.delay()

      Or: re_embed_all.delay(force=True)  # Also re-embeds already-complete docs
    """
    from rag_app.models import Document, DocumentChunk

    logger.warning('re_embed_all: Clearing all embeddings and starting fresh')

    # Clear all embeddings
    cleared = DocumentChunk.objects.exclude(embedding=None).update(
        embedding=None,
        embedding_dim=None,
    )
    logger.info(f're_embed_all: Cleared {cleared} embeddings')

    # Reset all document statuses to pending
    Document.objects.all().update(indexing_status='pending')

    # Dispatch individual embed tasks for each document
    docs = Document.objects.all()
    dispatched = 0
    for doc in docs:
        doc.indexing_status = 'processing'
        doc.save(update_fields=['indexing_status'])
        embed_chunks.delay(str(doc.id))
        dispatched += 1
        logger.info(f're_embed_all: Dispatched task for "{doc.title}"')

    logger.info(
        f're_embed_all: Complete. Dispatched {dispatched} embedding tasks. '
        f'Monitor progress: celery -A config worker --loglevel=info'
    )
    return dispatched


@app.task
def check_embedding_health():
    """
    Periodic task: check for documents with missing embeddings.
    Dispatches embed_chunks for any document in 'processing' or 'failed' state.

    Runs via Celery Beat:
      Add to CELERY_BEAT_SCHEDULE:
        'embedding-health-check': {
            'task': 'indexing_app.tasks.check_embedding_health',
            'schedule': crontab(hour='*/6'),  # Every 6 hours
        }
    """
    from rag_app.models import Document

    stuck_docs = Document.objects.filter(
        indexing_status__in=['processing', 'failed']
    )
    count = stuck_docs.count()

    if count > 0:
        logger.warning(
            f'check_embedding_health: Found {count} documents not complete. '
            f'Re-dispatching embed tasks.'
        )
        for doc in stuck_docs:
            embed_chunks.delay(str(doc.id))
    else:
        logger.info('check_embedding_health: All documents are complete ✓')

    return count






#======================= for local embedding =================



# indexing_app/tasks.py
# 
# import logging
# from config.celery import app
# 
# logger = logging.getLogger(__name__)
# 
# 
# @app.task(bind=True, max_retries=3, default_retry_delay=60)
# def embed_chunks(self, document_id: str, batch_size: int = 100):
#     """
#     Generate embeddings for all unembedded chunks of a document.
#     """
#     from rag_app.models import Document, DocumentChunk
#     from rag_app.embedding_service import get_embedding_service
# 
#     # Load document
#     try:
#         doc = Document.objects.get(pk=document_id)
#     except Document.DoesNotExist:
#         logger.error(f'embed_chunks: Document {document_id} not found — skipping')
#         return 0
# 
#     # Find all chunks without embeddings
#     chunks = list(
#         DocumentChunk.objects
#         .filter(document=doc, embedding__isnull=True)
#         .order_by('chunk_index')
#     )
# 
#     if not chunks:
#         logger.info(
#             f'embed_chunks: No unembedded chunks for "{doc.title}". '
#             f'Marking document as complete.'
#         )
#         doc.indexing_status = 'complete'
#         doc.save(update_fields=['indexing_status'])
#         return 0
# 
#     logger.info(
#         f'embed_chunks: Starting for "{doc.title}" — '
#         f'{len(chunks)} chunks to embed'
#     )
# 
#     try:
#         emb_svc = get_embedding_service()
#         # Expected dimension: 384 (all-MiniLM-L6-v2, all-mpnet-base-v2, etc.)
#         expected_dim = 384
#         total_embedded = 0
# 
#         for batch_start in range(0, len(chunks), batch_size):
#             batch = chunks[batch_start:batch_start + batch_size]
#             texts = [c.content for c in batch]
# 
#             logger.info(
#                 f'  Batch {batch_start // batch_size + 1} / '
#                 f'{(len(chunks) + batch_size - 1) // batch_size}: '
#                 f'{len(batch)} chunks'
#             )
# 
#             embeddings = emb_svc.get_batch_embeddings(texts)
# 
#             if not embeddings:
#                 raise RuntimeError(
#                     f'Embedding service returned empty list for batch starting at {batch_start}'
#                 )
# 
#             # Validate dimension matches expected 384
#             actual_dim = len(embeddings[0])
#             if actual_dim != expected_dim:
#                 raise ValueError(
#                     f'Embedding dimension mismatch: '
#                     f'got {actual_dim}, expected {expected_dim}. '
#                     f'Please ensure your embedding model produces 384-dimensional vectors.'
#                 )
# 
#             # Assign embeddings to chunk objects
#             for chunk, emb in zip(batch, embeddings):
#                 chunk.embedding = emb
#                 # Only set embedding_dim if the field exists
#                 if hasattr(chunk, 'embedding_dim'):
#                     chunk.embedding_dim = len(emb)
# 
#             # Determine which fields to update
#             update_fields = ['embedding']
#             if hasattr(DocumentChunk, 'embedding_dim'):
#                 update_fields.append('embedding_dim')
# 
#             # Bulk update
#             DocumentChunk.objects.bulk_update(
#                 batch,
#                 fields=update_fields,
#                 batch_size=50,
#             )
#             total_embedded += len(batch)
#             logger.info(f'  → {total_embedded}/{len(chunks)} embedded so far')
# 
#         # Mark document as complete
#         doc.indexing_status = 'complete'
#         doc.save(update_fields=['indexing_status'])
# 
#         logger.info(
#             f'embed_chunks: COMPLETE for "{doc.title}". '
#             f'{total_embedded} chunks embedded.'
#         )
#         return total_embedded
# 
#     except ValueError as e:
#         # Dimension mismatch — config error, don't retry
#         logger.error(f'embed_chunks FATAL (will not retry): {e}')
#         doc.indexing_status = 'failed'
#         doc.metadata = {**doc.metadata, 'embed_error': str(e)}
#         doc.save(update_fields=['indexing_status', 'metadata'])
#         raise
# 
#     except Exception as exc:
#         logger.error(
#             f'embed_chunks FAILED for "{doc.title}": {exc}',
#             exc_info=True,
#         )
#         doc.indexing_status = 'failed'
#         doc.save(update_fields=['indexing_status'])
#         raise self.retry(exc=exc)
# 
# 
# @app.task
# def re_embed_all(force: bool = False):
#     """
#     Admin task: Re-embed ALL document chunks from scratch.
#     """
#     from rag_app.models import Document, DocumentChunk
# 
#     logger.warning('re_embed_all: Clearing all embeddings and starting fresh')
# 
#     # Clear all embeddings
#     update_data = {'embedding': None}
#     if hasattr(DocumentChunk, 'embedding_dim'):
#         update_data['embedding_dim'] = None
#     
#     cleared = DocumentChunk.objects.exclude(embedding=None).update(**update_data)
#     logger.info(f're_embed_all: Cleared {cleared} embeddings')
# 
#     # Reset all document statuses to pending
#     Document.objects.all().update(indexing_status='pending')
# 
#     # Dispatch individual embed tasks for each document
#     docs = Document.objects.all()
#     dispatched = 0
#     for doc in docs:
#         doc.indexing_status = 'processing'
#         doc.save(update_fields=['indexing_status'])
#         embed_chunks.delay(str(doc.id))
#         dispatched += 1
#         logger.info(f're_embed_all: Dispatched task for "{doc.title}"')
# 
#     logger.info(
#         f're_embed_all: Complete. Dispatched {dispatched} embedding tasks.'
#     )
#     return dispatched
# 
# 
# @app.task
# def check_embedding_health():
#     """
#     Periodic task: check for documents with missing embeddings.
#     """
#     from rag_app.models import Document
# 
#     stuck_docs = Document.objects.filter(
#         indexing_status__in=['processing', 'failed']
#     )
#     count = stuck_docs.count()
# 
#     if count > 0:
#         logger.warning(
#             f'check_embedding_health: Found {count} documents not complete. '
#             f'Re-dispatching embed tasks.'
#         )
#         for doc in stuck_docs:
#             embed_chunks.delay(str(doc.id))
#     else:
#         logger.info('check_embedding_health: All documents are complete ✓')
# 
#     return count