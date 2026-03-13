import json
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline
from indexing_app.chunkers import chunk_comparative_topic

COMPARATIVE_FILE = 'data/comparative_religion/Islam_comparison_with_Christianity_and_Judaism.json'

class Command(BaseCommand):
    help = 'Load comparative religion dataset from data/comparative_religion/'

    def handle(self, *args, **kwargs):
        try:
            with open(COMPARATIVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f'ERROR: {COMPARATIVE_FILE} not found.')
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f'ERROR: Invalid JSON in {COMPARATIVE_FILE}: {e}')
            return

        pipeline = IndexingPipeline()
        loaded = 0
        skipped = 0

        # Handle different data structures
        topics_list = []
        if isinstance(data, dict):
            topics_list = data.get('topics', data.get('comparisons', []))
            metadata = data.get('metadata', {})
            self.stdout.write(
                f'Loaded: {metadata.get("title", "Comparative religion file")} '
                f'({metadata.get("total_topics", len(topics_list))} topics)'
            )
        elif isinstance(data, list):
            topics_list = data
        else:
            self.stderr.write('ERROR: Unexpected data structure in comparative religion file.')
            return

        chunks = []
        for topic in topics_list:
            topic_chunks = chunk_comparative_topic(topic)
            if topic_chunks:
                chunks.extend(topic_chunks)
            else:
                skipped += 1

        if chunks:
            pipeline.ingest_document('Comparative Religion: Islam vs Christianity & Judaism', 'comparative', chunks)
            loaded = len(chunks)

        self.stdout.write(f'Comparative religion done: {loaded} loaded, {skipped} skipped.')
