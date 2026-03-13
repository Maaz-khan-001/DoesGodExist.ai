import json
from django.core.management.base import BaseCommand

from indexing_app.pipeline import IndexingPipeline
from indexing_app.chunkers import chunk_hadith

HADITH_FILE = 'data/hadith/sahih_bukhari_final.json'

class Command(BaseCommand):
    help = 'Load Sahih Bukhari from data/hadith/sahih_bukhari_final.json'

    def handle(self, *args, **kwargs):
        try:
            with open(HADITH_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f'ERROR: {HADITH_FILE} not found.')
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f'ERROR: Invalid JSON in {HADITH_FILE}: {e}')
            return

        pipeline = IndexingPipeline()
        loaded = 0
        skipped = 0

        # Handle different data structures
        hadith_list = []
        if isinstance(data, dict):
            # File has wrapper: {"metadata": {...}, "hadiths": [...]}
            hadith_list = data.get('hadiths', [])
            metadata = data.get('metadata', {})
            self.stdout.write(
                f'Loaded: {metadata.get("title", "Hadith file")} '
                f'({metadata.get("total_hadiths", "?")} hadiths)'
            )
        elif isinstance(data, list):
            # Direct list of hadiths
            hadith_list = data
        else:
            self.stderr.write('ERROR: Unexpected data structure in hadith file.')
            return

        # Process hadith in batches for better performance
        batch_size = 100
        for i in range(0, len(hadith_list), batch_size):
            batch = hadith_list[i:i+batch_size]
            chunks = []
            batch_title = f"Sahih al-Bukhari {i+1}-{min(i+batch_size, len(hadith_list))}"
            
            for hadith in batch:
                hadith_chunks = chunk_hadith(hadith)
                if hadith_chunks:
                    chunks.extend(hadith_chunks)
                else:
                    skipped += 1
            
            if chunks:
                pipeline.ingest_document(batch_title, 'hadith', chunks)
                loaded += len(chunks)
                
                if loaded % 500 == 0:
                    self.stdout.write(f'Indexed {loaded} hadith chunks...')

        self.stdout.write(f'Hadith done: {loaded} loaded, {skipped} skipped.')
