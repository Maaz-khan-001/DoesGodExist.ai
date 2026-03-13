import json
import os
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline
from indexing_app.chunkers import chunk_philosophy_argument

# 3 philosophy files — one per stage (no stage 4 philosophy file)
PHILOSOPHY_FILES = [
    ('data/philosphy/stage1_existence_of_god.json',        1),
    ('data/philosphy/stage2_necessity_of_prophethood.json', 2),
    ('data/philosphy/stage3_prophethood_of_muhammad.json', 3),
]

class Command(BaseCommand):
    help = 'Load philosophy arguments from stage files'

    def handle(self, *args, **kwargs):
        pipeline = IndexingPipeline()
        total_loaded = 0
        total_skipped = 0

        for file_path, stage_int in PHILOSOPHY_FILES:
            if not os.path.exists(file_path):
                self.stderr.write(f'WARNING: {file_path} not found, skipping.')
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stderr.write(f'ERROR: Invalid JSON in {file_path}: {e}')
                continue

            # Handle different data structures
            args_list = []
            if isinstance(data, dict):
                args_list = data.get('arguments', [])
                metadata = data.get('metadata', {})
                self.stdout.write(
                    f'Processing {os.path.basename(file_path)}: '
                    f'{metadata.get("title", "Philosophy file")} '
                    f'({len(args_list)} arguments)'
                )
            elif isinstance(data, list):
                args_list = data
            else:
                self.stderr.write(f'ERROR: Unexpected data structure in {file_path}')
                continue

            chunks = []
            for argument in args_list:
                arg_chunks = chunk_philosophy_argument(argument, stage_int)
                if arg_chunks:
                    chunks.extend(arg_chunks)
                else:
                    total_skipped += 1

            if chunks:
                title = f'Philosophy Stage {stage_int} Arguments'
                pipeline.ingest_document(title, 'philosophy', chunks)
                total_loaded += len(chunks)
                self.stdout.write(f'  Loaded {len(chunks)} philosophy chunks')

        self.stdout.write(f'Philosophy done: {total_loaded} loaded, {total_skipped} skipped.')
