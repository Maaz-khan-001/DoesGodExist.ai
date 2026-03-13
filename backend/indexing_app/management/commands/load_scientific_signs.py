"""
management/commands/load_scientific_signs.py

JSON structure: bare root-level list  [ { "id": "QC023", ... }, ... ]

DocumentChunk fields used:
  content          ← main text body
  content_arabic   ← arabic_text field from entry
  chunk_type       ← 'core_claim' | 'scholarly_context' | 'debate_analysis'
  stage_tags       ← debate_stage list  e.g. [1, 3] → ['stage_1', 'stage_3']
  topic_tags       ← [source_type, scientific_field, importance, evidence_strength]
  source_ref       ← structured dict with id, reference, discovery info
  token_count      ← rough estimate: len(content.split())
"""

import json
from django.core.management.base import BaseCommand
from indexing_app.pipeline import IndexingPipeline

SCIENCE_FILE = 'data/science_and_religion/scientific_signs_quran_hadith_v2.json'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_entries(data) -> list:
    if isinstance(data, list):
        return data
    for key in ('new_entries', 'entries', 'scientific_signs'):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


def _stage_tags(debate_stage: list) -> list:
    """Convert [1, 3] → ['stage_1', 'stage_3']"""
    return [f'stage_{s}' for s in debate_stage if isinstance(s, int)]


def _token_count(text: str) -> int:
    return len(text.split())


def _chunk_entry(entry: dict) -> list:
    """Convert one entry into up to 3 DocumentChunk-compatible dicts. Returns [] if invalid."""
    if not entry.get('id') or not entry.get('scientific_claim_summary'):
        return []

    entry_id    = entry['id']
    source_type = entry.get('source_type', 'Quran')
    reference   = entry.get('reference', '')
    field       = entry.get('scientific_field', '')
    arabic      = entry.get('arabic_text', None)

    stage_tags  = _stage_tags(entry.get('debate_stage', []))
    topic_tags  = [t for t in [
        source_type.lower(),
        field.lower()[:50] if field else None,
        entry.get('importance', '').lower().replace(' ', '_') or None,
        entry.get('evidence_strength', '').lower() or None,
    ] if t]

    disc = entry.get('scientific_discovery', {})
    source_ref = {
        'entry_id':    entry_id,
        'reference':   reference,
        'source_type': source_type,
        'discovered_by': disc.get('discovered_by', ''),
        'discovery_year': disc.get('year', ''),
        'discovery_field': disc.get('scientific_field', ''),
        'evidence_strength': entry.get('evidence_strength', ''),
        'importance': entry.get('importance', ''),
    }

    chunks = []

    # ── Chunk 1: Core claim ──────────────────────────────────────────────────
    lines = [f'[{source_type}] {reference} — {field}']
    if entry.get('translation'):
        lines.append(f"Translation: {entry['translation']}")
    lines.append(f"Scientific Claim: {entry['scientific_claim_summary']}")
    if disc:
        lines.append(
            f"Discovery: {disc.get('discovered_by', '')} "
            f"({disc.get('year', '')}) — {disc.get('scientific_field', '')}"
        )
    content = '\n'.join(lines)
    chunks.append({
        'content':        content,
        'content_arabic': arabic,
        'chunk_type':     'core_claim',
        'stage_tags':     stage_tags,
        'topic_tags':     topic_tags,
        'source_ref':     source_ref,
        'token_count':    _token_count(content),
    })

    # ── Chunk 2: Scholarly context ───────────────────────────────────────────
    parts = []
    if entry.get('classical_tafsir_position'):
        parts.append(f"Classical Tafsir: {entry['classical_tafsir_position']}")
    if entry.get('modern_scientific_parallel'):
        parts.append(f"Modern Parallel: {entry['modern_scientific_parallel']}")
    if entry.get('scholarly_support'):
        parts.append(f"Scholarly Support: {entry['scholarly_support']}")
    if parts:
        content = f'[{source_type}] {reference} — Scholarly Context:\n' + '\n'.join(parts)
        chunks.append({
            'content':        content,
            'content_arabic': None,
            'chunk_type':     'scholarly_context',
            'stage_tags':     stage_tags,
            'topic_tags':     topic_tags,
            'source_ref':     source_ref,
            'token_count':    _token_count(content),
        })

    # ── Chunk 3: Debate analysis ─────────────────────────────────────────────
    parts = []
    if entry.get('major_criticisms'):
        parts.append(f"Major Criticisms: {entry['major_criticisms']}")
    if entry.get('rebuttal_summary'):
        parts.append(f"Rebuttal: {entry['rebuttal_summary']}")
    if entry.get('usage_guideline'):
        parts.append(f"Usage Guideline: {entry['usage_guideline']}")
    if parts:
        content = f'[{source_type}] {reference} — Debate Analysis:\n' + '\n'.join(parts)
        chunks.append({
            'content':        content,
            'content_arabic': None,
            'chunk_type':     'debate_analysis',
            'stage_tags':     stage_tags,
            'topic_tags':     topic_tags,
            'source_ref':     source_ref,
            'token_count':    _token_count(content),
        })

    return chunks


# ── Django Command ────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Load scientific signs dataset from data/science_and_religion/'

    def handle(self, *args, **kwargs):
        try:
            with open(SCIENCE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f'ERROR: {SCIENCE_FILE} not found.')
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f'ERROR: Invalid JSON: {e}')
            return

        entries = _get_entries(data)
        self.stdout.write(f'Found {len(entries)} entries.')

        if not entries:
            self.stderr.write('ERROR: No entries found. Expected root-level JSON array or dict with "new_entries" key.')
            return

        pipeline        = IndexingPipeline()
        chunks, skipped = [], 0

        for entry in entries:
            entry_chunks = _chunk_entry(entry)
            if entry_chunks:
                chunks.extend(entry_chunks)
            else:
                skipped += 1
                self.stdout.write(f'  SKIPPED: {entry.get("id", "unknown")} — missing id or scientific_claim_summary')

        if chunks:
            try:
                pipeline.ingest_document('Scientific Signs in Quran and Hadith', 'scientific', chunks)
                self.stdout.write(self.style.SUCCESS(
                    f'Scientific signs done: {len(chunks)} chunks loaded, {skipped} entries skipped.'
                ))
            except Exception as e:
                self.stderr.write(f'ERROR during ingestion: {e}')
        else:
            self.stdout.write(self.style.WARNING('No chunks produced. Check entry structure.'))