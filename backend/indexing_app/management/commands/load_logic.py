

import json
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline

LOGIC_FILE = 'data/logic/reasoning_framework.json'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_entries(data: dict) -> list:
    """
    Walk data['sections'] and return (section_type, entry) pairs.
    Falls back to top-level keys if 'sections' is absent.
    """
    pairs = []
    sections = data.get('sections')
    source   = sections if isinstance(sections, dict) else {k: v for k, v in data.items() if k != 'metadata'}

    for section_type, entries in source.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                pairs.append((section_type, entry))
    return pairs


def _stage_tags(debate_stage: list) -> list:
    """Convert [1, 2, 3] → ['stage_1', 'stage_2', 'stage_3']"""
    return [f'stage_{s}' for s in debate_stage if isinstance(s, int)]


def _token_count(text: str) -> int:
    return len(text.split())


def _chunk_entry(entry: dict, section_type: str) -> list:
    """Convert one logic entry into up to 3 DocumentChunk-compatible dicts. Returns [] if invalid."""
    if not entry.get('id') or not entry.get('definition'):
        return []

    entry_id = entry['id']
    name     = entry.get('name', entry_id)
    severity = entry.get('severity_level', '')

    stage_tags = _stage_tags(entry.get('debate_stage', []))
    topic_tags = [t for t in [
        section_type.lower(),
        severity.lower() or None,
    ] if t]

    source_ref = {
        'entry_id':       entry_id,
        'name':           name,
        'section_type':   section_type,
        'severity_level': severity,
    }

    chunks = []

    # ── Chunk 1: Definition ──────────────────────────────────────────────────
    content = (
        f'[{section_type}] {name} ({entry_id})\n'
        f"Definition: {entry['definition']}"
    )
    chunks.append({
        'content':     content,
        'chunk_type':  'definition',
        'stage_tags':  stage_tags,
        'topic_tags':  topic_tags,
        'source_ref':  source_ref,
        'token_count': _token_count(content),
    })

    # ── Chunk 2: Example ─────────────────────────────────────────────────────
    if entry.get('example'):
        content = f'[{section_type}] {name} — Example:\n{entry["example"]}'
        chunks.append({
            'content':     content,
            'chunk_type':  'example',
            'stage_tags':  stage_tags,
            'topic_tags':  topic_tags,
            'source_ref':  source_ref,
            'token_count': _token_count(content),
        })

    # ── Chunk 3: Strategy + usage notes ─────────────────────────────────────
    parts = []
    if entry.get('reframing_strategy'):
        parts.append(f"Reframing Strategy: {entry['reframing_strategy']}")
    if entry.get('usage_notes'):
        parts.append(f"Usage Notes: {entry['usage_notes']}")
    if parts:
        content = f'[{section_type}] {name} — Strategy & Notes:\n' + '\n'.join(parts)
        chunks.append({
            'content':     content,
            'chunk_type':  'strategy',
            'stage_tags':  stage_tags,
            'topic_tags':  topic_tags,
            'source_ref':  source_ref,
            'token_count': _token_count(content),
        })

    return chunks


# ── Django Command ────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Load logic/reasoning framework from data/logic/'

    def handle(self, *args, **kwargs):
        try:
            with open(LOGIC_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f'ERROR: {LOGIC_FILE} not found.')
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f'ERROR: Invalid JSON: {e}')
            return

        entry_pairs = _get_entries(data)
        sections    = list(data.get('sections', {}).keys())

        self.stdout.write(f'Found {len(entry_pairs)} entries | Sections: {sections}')

        if not entry_pairs:
            self.stderr.write('ERROR: No entries found. Expected data["sections"] with list-valued keys.')
            return

        pipeline        = IndexingPipeline()
        chunks, skipped = [], 0

        for section_type, entry in entry_pairs:
            entry_chunks = _chunk_entry(entry, section_type)
            if entry_chunks:
                chunks.extend(entry_chunks)
            else:
                skipped += 1
                self.stdout.write(
                    f'  SKIPPED: {entry.get("id", "unknown")} in [{section_type}] — missing id or definition'
                )

        if chunks:
            try:
                pipeline.ingest_document('Logic and Reasoning Framework', 'logic', chunks)
                self.stdout.write(self.style.SUCCESS(
                    f'Logic done: {len(chunks)} chunks loaded, {skipped} entries skipped.'
                ))
            except Exception as e:
                self.stderr.write(f'ERROR during ingestion: {e}')
        else:
            self.stdout.write(self.style.WARNING('No chunks produced. Check entry structure.'))