import hashlib
from rag_app.models import Document, DocumentChunk


class IndexingPipeline:
    def ingest_document(self, title, source_type, chunks_data, metadata=None):
        """
        Idempotent document ingestion.
        Safe to re-run — will skip already-indexed documents.

        After this runs, call:
          python manage.py generate_embeddings --sync
        to generate embeddings for all loaded documents.
        """
        checksum = hashlib.sha256(title.encode()).hexdigest()

        doc, created = Document.objects.get_or_create(
            checksum=checksum,
            defaults={
                'title': title,
                'source_type': source_type,
                'metadata': metadata or {},
            }
        )

        if not created and doc.indexing_status == 'complete':
            print(f'Skipping [{title}] — already indexed ({doc.chunk_count} chunks)')
            return doc

        doc.indexing_status = 'processing'
        doc.save(update_fields=['indexing_status'])

        created_count = 0
        for i, chunk_data in enumerate(chunks_data):
            _, chunk_created = DocumentChunk.objects.get_or_create(
                document=doc,
                chunk_index=i,
                defaults=chunk_data
            )
            if chunk_created:
                created_count += 1

        doc.chunk_count = DocumentChunk.objects.filter(document=doc).count()
        # 'complete' = chunks loaded. generate_embeddings finds un-embedded
        # chunks via embedding__isnull=True, regardless of this status.
        doc.indexing_status = 'complete'
        doc.save(update_fields=['chunk_count', 'indexing_status'])

        print(f'Indexed [{title}]: {created_count} new chunks')
        return doc