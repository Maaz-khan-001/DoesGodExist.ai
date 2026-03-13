import json
import os
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline
from indexing_app.chunkers import chunk_debate_topic, chunk_glossary_term

DEBATE_TOPICS_FILE = 'data/meta/debate_topics.json'
GLOSSARY_FILE = 'data/meta/glossary.json'

class Command(BaseCommand):
    help = 'Load meta dataset (debate topics + glossary) from data/meta/'

    def handle(self, *args, **kwargs):
        pipeline = IndexingPipeline()
        total_loaded = 0
        total_skipped = 0

        # Load debate topics
        if os.path.exists(DEBATE_TOPICS_FILE):
            try:
                with open(DEBATE_TOPICS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stderr.write(f'ERROR: Invalid JSON in {DEBATE_TOPICS_FILE}: {e}')
            else:
                topics_list = []
                if isinstance(data, dict):
                    topics_list = data.get('topics', data.get('debate_topics', []))
                    metadata = data.get('metadata', {})
                    self.stdout.write(
                        f'Processing debate topics: {metadata.get("title", "Debate topics file")} '
                        f'({len(topics_list)} topics)'
                    )
                elif isinstance(data, list):
                    topics_list = data
                else:
                    self.stderr.write('ERROR: Unexpected data structure in debate topics file.')

                chunks = []
                for topic in topics_list:
                    # Default to existence stage for debate topics
                    topic_chunks = chunk_debate_topic(topic, 'existence')
                    if topic_chunks:
                        chunks.extend(topic_chunks)
                    else:
                        total_skipped += 1

                if chunks:
                    pipeline.ingest_document('Debate Topics', 'meta', chunks)
                    total_loaded += len(chunks)
                    self.stdout.write(f'  Loaded {len(chunks)} debate topic chunks')
        else:
            self.stderr.write(f'WARNING: {DEBATE_TOPICS_FILE} not found, skipping.')

        # Load glossary
        if os.path.exists(GLOSSARY_FILE):
            try:
                with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stderr.write(f'ERROR: Invalid JSON in {GLOSSARY_FILE}: {e}')
            else:
                chunks = []
                glossary_sections = ['core_concepts', 'philosophical_terms']
                
                for section in glossary_sections:
                    if isinstance(data, dict) and section in data:
                        self.stdout.write(f'Processing glossary {section}: {len(data[section])} terms')
                        for term, definition in data[section].items():
                            term_chunks = chunk_glossary_term(term, definition)
                            if term_chunks:
                                chunks.extend(term_chunks)
                            else:
                                total_skipped += 1

                if chunks:
                    pipeline.ingest_document('Glossary', 'meta', chunks)
                    total_loaded += len(chunks)
                    self.stdout.write(f'  Loaded {len(chunks)} glossary chunks')
        else:
            self.stderr.write(f'WARNING: {GLOSSARY_FILE} not found, skipping.')

        self.stdout.write(f'Meta done: {total_loaded} loaded, {total_skipped} skipped.')
