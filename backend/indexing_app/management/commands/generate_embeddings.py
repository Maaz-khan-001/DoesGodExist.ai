import time
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Generate embeddings for all un-embedded document chunks.

    Usage:
      python manage.py generate_embeddings --sync          # Run directly (no Celery needed) ← LOCAL DEV
      python manage.py generate_embeddings --status        # Show embedding progress only
      python manage.py generate_embeddings --document-id <uuid> --sync   # Single document
      python manage.py generate_embeddings --failed --sync # Retry only failed documents
    """

    help = 'Generate embeddings for un-embedded knowledge base chunks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run embeddings directly in this process (no Celery). '
                 'Required for local dev.',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current embedding status for all documents and exit.',
        )
        parser.add_argument(
            '--document-id',
            type=str,
            dest='document_id',
            help='Only embed chunks for the given document UUID.',
        )
        parser.add_argument(
            '--failed',
            action='store_true',
            help='Retry only documents with indexing_status=failed.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            dest='batch_size',
            help='Number of chunks per embedding call (default: 100).',
        )

    def handle(self, *args, **options):
        from rag_app.models import Document, DocumentChunk

        # ── Status report ────────────────────────────────────────────────────
        if options['status']:
            self._print_status()
            return

        # ── Select documents to process ──────────────────────────────────────
        if options['document_id']:
            try:
                docs = [Document.objects.get(pk=options['document_id'])]
            except Document.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Document {options['document_id']} not found.")
                )
                return
        elif options['failed']:
            docs = list(Document.objects.filter(indexing_status='failed'))
            if not docs:
                self.stdout.write(self.style.SUCCESS('No failed documents found.'))
                return
        else:
            # All documents that have un-embedded chunks
            docs = list(
                Document.objects.filter(
                    chunks__embedding__isnull=True,
                    deleted_at__isnull=True,
                ).distinct()
            )

        if not docs:
            self.stdout.write(self.style.SUCCESS(
                '✓ All chunks are already embedded. Nothing to do.'
            ))
            self._print_status()
            return

        total_unembedded = DocumentChunk.objects.filter(
            document__in=docs,
            embedding__isnull=True,
        ).count()

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\n'
            f'  Generating Embeddings\n'
            f'  Documents : {len(docs)}\n'
            f'  Chunks    : {total_unembedded} un-embedded\n'
            f'  Mode      : {"synchronous (direct)" if options["sync"] else "Celery async"}\n'
            f'{"=" * 60}\n'
        ))

        if options['sync']:
            self._run_sync(docs, options['batch_size'])
        else:
            self.stdout.write(self.style.ERROR(
                'ERROR: --sync flag is required for local dev (no Celery).\n'
                'Run: python manage.py generate_embeddings --sync'
            ))

    def _run_sync(self, docs, batch_size):
        """Embed chunks directly in this process — no Celery needed."""
        from rag_app.models import DocumentChunk
        from rag_app.embedding_service import get_embedding_service

        self.stdout.write('  Loading embedding model (first run downloads ~90MB)...')
        try:
            emb_svc = get_embedding_service()
            self.stdout.write(self.style.SUCCESS('  ✓ Embedding model ready\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed to load model: {e}'))
            return

        start = time.time()
        total_embedded = 0
        failures = []

        for doc_index, doc in enumerate(docs, 1):
            self.stdout.write(
                f'[{doc_index}/{len(docs)}] {doc.title} '
                f'(status: {doc.indexing_status})'
            )

            chunks = list(
                DocumentChunk.objects
                .filter(document=doc, embedding__isnull=True)
                .order_by('chunk_index')
            )

            if not chunks:
                self.stdout.write(self.style.SUCCESS('  ✓ Already fully embedded — skipping'))
                doc.indexing_status = 'complete'
                doc.save(update_fields=['indexing_status'])
                continue

            self.stdout.write(f'  Embedding {len(chunks)} chunks...')

            try:
                doc.indexing_status = 'processing'
                doc.save(update_fields=['indexing_status'])

                doc_embedded = 0
                num_batches = (len(chunks) + batch_size - 1) // batch_size

                for batch_start in range(0, len(chunks), batch_size):
                    batch = chunks[batch_start:batch_start + batch_size]
                    texts = [c.content for c in batch]
                    batch_num = batch_start // batch_size + 1

                    embeddings = emb_svc.get_batch_embeddings(texts)

                    if not embeddings:
                        raise RuntimeError(f'Empty embeddings returned for batch {batch_num}')

                    actual_dim = len(embeddings[0])
                    expected_dim = 384  # all-MiniLM-L6-v2
                    if actual_dim != expected_dim:
                        raise ValueError(
                            f'Dimension mismatch: got {actual_dim}, expected {expected_dim}. '
                            f'Check EMBEDDING_BACKEND in your .env'
                        )

                    for chunk, emb in zip(batch, embeddings):
                        chunk.embedding = emb
                        if hasattr(chunk, 'embedding_dim'):
                            chunk.embedding_dim = actual_dim

                    update_fields = ['embedding']
                    if hasattr(DocumentChunk, 'embedding_dim'):
                        update_fields.append('embedding_dim')

                    DocumentChunk.objects.bulk_update(
                        batch, fields=update_fields, batch_size=50
                    )
                    doc_embedded += len(batch)
                    total_embedded += len(batch)

                    # Progress per batch so it doesn't look frozen
                    elapsed = time.time() - start
                    self.stdout.write(
                        f'  Batch {batch_num}/{num_batches} — '
                        f'{doc_embedded}/{len(chunks)} chunks — '
                        f'{total_embedded} total — '
                        f'{elapsed:.0f}s elapsed'
                    )

                doc.indexing_status = 'complete'
                doc.save(update_fields=['indexing_status'])
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Done: {doc_embedded} chunks embedded'
                ))

            except ValueError as e:
                failures.append((doc.title, str(e)))
                doc.indexing_status = 'failed'
                doc.save(update_fields=['indexing_status'])
                self.stdout.write(self.style.ERROR(f'  ✗ Config error (will not retry): {e}'))

            except Exception as e:
                failures.append((doc.title, str(e)))
                doc.indexing_status = 'failed'
                doc.save(update_fields=['indexing_status'])
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {e}'))

        elapsed = time.time() - start
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\n'
            f'  Done ({elapsed:.1f}s)\n'
            f'{"=" * 60}'
        ))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Total embedded : {total_embedded} chunks'))
        if failures:
            self.stdout.write(self.style.ERROR(f'  ✗ Failures       : {len(failures)}'))
            for title, err in failures:
                self.stdout.write(self.style.ERROR(f'    - {title}: {err}'))

        self._print_status()

    def _print_status(self):
        """Print a summary table of embedding progress per document."""
        from rag_app.models import Document, DocumentChunk

        docs = Document.objects.filter(deleted_at__isnull=True).order_by('source_type', 'title')

        if not docs.exists():
            self.stdout.write('No documents found.')
            return

        total_chunks = DocumentChunk.objects.filter(deleted_at__isnull=True).count()
        embedded = DocumentChunk.objects.filter(
            deleted_at__isnull=True, embedding__isnull=False
        ).count()
        missing = total_chunks - embedded
        pct = (embedded / total_chunks * 100) if total_chunks else 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 70}\n'
            f'  Embedding Status\n'
            f'  Total chunks : {total_chunks}  |  '
            f'Embedded : {embedded}  |  '
            f'Missing : {missing}  |  '
            f'{pct:.1f}% complete\n'
            f'{"=" * 70}'
        ))
        self.stdout.write(
            f'\n  {"Status":<12} {"Source":<22} {"Chunks":>7} {"Embedded":>9} {"Missing":>8}  Title'
        )
        self.stdout.write('  ' + '-' * 68)

        for doc in docs:
            doc_chunks = DocumentChunk.objects.filter(document=doc, deleted_at__isnull=True)
            doc_total = doc_chunks.count()
            doc_embedded = doc_chunks.filter(embedding__isnull=False).count()
            doc_missing = doc_total - doc_embedded

            status_color = (
                self.style.SUCCESS if doc.indexing_status == 'complete'
                else self.style.ERROR if doc.indexing_status == 'failed'
                else self.style.WARNING
            )
            status_str = status_color(f'{doc.indexing_status:<12}')

            missing_str = (
                self.style.ERROR(f'{doc_missing:>8}') if doc_missing > 0
                else f'{doc_missing:>8}'
            )

            title = doc.title[:35] + '…' if len(doc.title) > 36 else doc.title
            self.stdout.write(
                f'  {status_str} {doc.source_type:<22} {doc_total:>7} {doc_embedded:>9} {missing_str}  {title}'
            )

        self.stdout.write('')