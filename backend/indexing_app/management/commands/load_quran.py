import json
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline
from indexing_app.chunkers import chunk_quran_verse

QURAN_FILE = 'data/Quran/quran_debate_ready_FINAL.json'


class Command(BaseCommand):
    help = 'Load Quran from data/Quran/quran_debate_ready_FINAL.json'

    def handle(self, *args, **kwargs):
        try:
            with open(QURAN_FILE, 'r', encoding='utf-8') as f:
                verses = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f'ERROR: {QURAN_FILE} not found.')
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f'ERROR: Invalid JSON in {QURAN_FILE}: {e}')
            return

        # Handle both a bare list and a dict wrapper {"verses": [...]}
        if isinstance(verses, dict):
            verses = verses.get('verses') or verses.get('data') or []

        pipeline = IndexingPipeline()
        loaded = skipped = 0

        for v in verses:
            surah = v.get('surah')
            ayah  = v.get('ayah')

            if surah is None or ayah is None:
                skipped += 1
                continue

            chunks = chunk_quran_verse(v)
            if not chunks:
                skipped += 1
                continue

            pipeline.ingest_document(
                title=f'Quran {surah}:{ayah}',
                source_type='quran',
                chunks_data=chunks,
            )
            loaded += 1

            if loaded % 500 == 0:
                self.stdout.write(f'  ...{loaded} verses processed')

        self.stdout.write(self.style.SUCCESS(
            f'Quran done: {loaded} loaded, {skipped} skipped.'
        ))

