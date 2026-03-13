import tiktoken

ENCODER = tiktoken.get_encoding('cl100k_base')

# ── Stage normalisation ───────────────────────────────────────────────────────
# Dataset uses integers (1-4) and verbose strings.
# Internal system uses short strings: existence / prophethood / muhammad / invitation

STAGE_INT_MAP = {
    1: 'existence',
    2: 'prophethood',
    3: 'muhammad',
    4: 'invitation',
}

STAGE_STR_MAP = {
    'existence_of_god':           'existence',
    'necessity_of_prophethood':   'prophethood',
    'prophethood_of_muhammad':    'muhammad',
    'invitation_to_islam':        'invitation',
    'monotheism':                 'existence',
    'moral_framework':            'existence',
    'ethical_framework':          'invitation',
    'natural_evidence':           'existence',
    'fitrah':                     'existence',
    'historical_authenticity':    'muhammad',
    'interfaith_dialogue':        'invitation',
    'comparative_theology':       'invitation',
}


def normalise_stages(raw_stages: list) -> list:
    """
    Convert a mixed list of ints and/or verbose strings to internal stage strings.
    Deduplicates. Falls back gracefully for any unrecognised value.
    """
    result = []
    for s in raw_stages:
        if isinstance(s, int):
            mapped = STAGE_INT_MAP.get(s)
        else:
            mapped = STAGE_STR_MAP.get(str(s).lower().strip())
            if not mapped:
                # Last resort: keep it, just clean it up
                mapped = str(s).lower().strip().replace(' ', '_')
        if mapped and mapped not in result:
            result.append(mapped)
    return result if result else ['existence']


def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))


# ── 1. Quran chunker ─────────────────────────────────────────────────────────

def chunk_quran_verse(verse: dict) -> list:
    """
    Parse one verse object from quran_debate_ready_FINAL.json.
    One ayah = exactly one chunk. Never split.

    Input fields used:
      verse['surah'], verse['ayah'], verse['reference']
      verse['arabic']
      verse['translations']['english'], verse['translations']['urdu']
      verse['debate_stage_tags']   — list of verbose stage strings
      verse['topic_tags']          — list of topic strings
      verse['summary']             — brief description (stored in metadata)
      verse['theological_role']    — stored in metadata
      verse['usage_notes']         — stored in metadata
      verse['confidence_level']
    """
    translations = verse.get('translations', {})
    english = translations.get('english', '').strip()
    urdu = translations.get('urdu', '').strip() or None
    arabic = verse.get('arabic', '').strip() or None

    if not english:
        return []

    stage_tags = normalise_stages(verse.get('debate_stage_tags', []))
    topic_tags = [t.lower().strip() for t in verse.get('topic_tags', [])]

    return [{
        'content':        english,
        'content_arabic': arabic,
        'content_urdu':   urdu,
        'chunk_type':     'quran',
        'token_count':    count_tokens(english),
        'stage_tags':     stage_tags,
        'topic_tags':     topic_tags,
        'source_ref': {
            'surah':      verse.get('surah'),
            'ayah':       verse.get('ayah'),
            'reference':  verse.get('reference', ''),
            'surah_name_english': verse.get('surah_name_english', ''),
            'surah_name_arabic':  verse.get('surah_name_arabic', ''),
            'theological_role':   verse.get('theological_role', ''),
            'summary':            verse.get('summary', ''),
            'usage_notes':        verse.get('usage_notes', ''),
            'confidence_level':   verse.get('confidence_level', 'standard'),
        },
        'is_verified': True,
    }]


# ── 2. Hadith chunker ────────────────────────────────────────────────────────

def chunk_hadith(hadith: dict) -> list:
    """
    Parse one hadith object from sahih_bukhari_final.json.

    Input fields used:
      hadith['hadith_number']
      hadith['book'], hadith['book_number']
      hadith['full_text']['english'], ['arabic'], ['urdu']
      hadith['authentication']         — 'Sahih' / 'Hasan' etc.
      hadith['confidence_level']       — 'highest' / 'high' etc.
      hadith['stage']                  — list of ints [2, 4]
      hadith['debate_stage_tags']      — list of verbose strings
      hadith['topic_tags']
      hadith['summary']
      hadith['theological_role']
      hadith['cross_references']
      hadith['usage_notes']
    """
    full_text = hadith.get('full_text', {})
    english = full_text.get('english', '').strip()
    arabic  = full_text.get('arabic', '').strip() or None
    urdu    = full_text.get('urdu', '').strip() or None

    if not english:
        return []

    # Use stage array (integers) if present; fall back to debate_stage_tags strings
    raw_stages = hadith.get('stage') or hadith.get('debate_stage_tags', [])
    stage_tags = normalise_stages(raw_stages)
    topic_tags = [t.lower().strip() for t in hadith.get('topic_tags', [])]

    authentication = hadith.get('authentication', '').lower()
    # All Bukhari are Sahih. Accept 'sahih' and 'hasan' as verified.
    is_verified = authentication in ['sahih', 'hasan']

    return [{
        'content':        english,
        'content_arabic': arabic,
        'content_urdu':   urdu,
        'chunk_type':     'hadith',
        'token_count':    count_tokens(english),
        'stage_tags':     stage_tags,
        'topic_tags':     topic_tags,
        'source_ref': {
            'collection':        hadith.get('source', 'Sahih al-Bukhari'),
            'number':            str(hadith.get('hadith_number', '')),
            'book':              hadith.get('book', ''),
            'book_number':       hadith.get('book_number'),
            'grade':             hadith.get('authentication', 'Sahih'),
            'confidence_level':  hadith.get('confidence_level', 'highest'),
            'theological_role':  hadith.get('theological_role', ''),
            'summary':           hadith.get('summary', ''),
            'cross_references':  hadith.get('cross_references', []),
            'usage_notes':       hadith.get('usage_notes', ''),
        },
        'is_verified': is_verified,
    }]


# ── 3. Philosophy chunker ────────────────────────────────────────────────────

def chunk_philosophy_argument(argument: dict, stage_int: int) -> list:
    """
    Parse one argument object from philosophy/stage{N}_*.json.

    Each argument becomes ONE chunk containing:
      - name + category
      - all premises (numbered)
      - conclusion
      - key responses to common objections (condensed)
      - linked Quran verses (for context, not primary citation)

    Input fields:
      argument['id'], argument['name'], argument['category']
      argument['premises']         — list of strings
      argument['conclusion']
      argument['common_objections']
      argument['responses']
      argument['linked_quran_verses'] — [{'reference': '52:35', 'text': '...'}]
      argument['strength_level']
    """
    name      = argument.get('name', '')
    category  = argument.get('category', '')
    premises  = argument.get('premises', [])
    conclusion = argument.get('conclusion', '')
    responses = argument.get('responses', [])
    objections = argument.get('common_objections', [])
    linked_verses = argument.get('linked_quran_verses', [])

    # Build human-readable chunk text
    lines = [
        f'## {name}',
        f'Category: {category}',
        '',
        '### Premises',
    ]
    lines.extend(premises)
    lines.append('')
    lines.append(f'### Conclusion\n{conclusion}')

    if responses:
        lines.append('')
        lines.append('### Responses to Objections')
        for i, (obj, resp) in enumerate(zip(objections, responses), 1):
            lines.append(f'{i}. Objection: {obj}')
            lines.append(f'   Response: {resp}')

    if linked_verses:
        lines.append('')
        lines.append('### Related Quran Verses')
        for v in linked_verses:
            lines.append(f"Quran {v.get('reference')}: {v.get('text', '')}")

    content = '\n'.join(lines)
    stage_str = STAGE_INT_MAP.get(stage_int, 'existence')

    return [{
        'content':        content,
        'content_arabic': None,
        'content_urdu':   None,
        'chunk_type':     'philosophy',
        'token_count':    count_tokens(content),
        'stage_tags':     [stage_str],
        'topic_tags':     [category.lower().replace(' ', '_'), 'argument',
                           argument.get('id', '').lower()],
        'source_ref': {
            'id':            argument.get('id', ''),
            'name':          name,
            'category':      category,
            'strength_level': argument.get('strength_level', ''),
        },
        'is_verified': False,
    }]


# ── 4. Scientific signs chunker ──────────────────────────────────────────────

def chunk_scientific_sign(entry: dict) -> list:
    """
    Parse one entry from scientific_signs_quran_hadith_v2.json.

    Each entry becomes ONE chunk containing:
      - reference + translation
      - scientific claim summary
      - evidence strength
      - key rebuttal summary (for balanced debate)
      - usage guideline

    Input fields:
      entry['id'], entry['source_type'], entry['reference']
      entry['arabic_text'], entry['translation']
      entry['scientific_field']
      entry['scientific_claim_summary']
      entry['evidence_strength']
      entry['rebuttal_summary']
      entry['usage_guideline']
      entry['debate_stage']    — list of ints [1, 3]
      entry['importance']      — 'primary for scientific' / 'supportive'
    """
    translation = entry.get('translation', '').strip()
    if not translation:
        return []

    sci_summary   = entry.get('scientific_claim_summary', '')
    rebuttal      = entry.get('rebuttal_summary', '')
    guideline     = entry.get('usage_guideline', '')
    sci_field     = entry.get('scientific_field', '')
    evidence_str  = entry.get('evidence_strength', '')

    content = (
        f"Quran {entry.get('reference', '')}:\n"
        f"{translation}\n\n"
        f"Scientific Field: {sci_field}\n"
        f"Scientific Claim: {sci_summary}\n"
    )
    if rebuttal:
        content += f"\nRebuttal to consider: {rebuttal}\n"
    if guideline:
        content += f"\nUsage: {guideline}\n"

    stage_tags = normalise_stages(entry.get('debate_stage', [1]))
    importance = entry.get('importance', '')
    topic_tags = [sci_field.lower().replace(' ', '_').replace('-', '_'),
                  'scientific_sign', evidence_str.replace(' ', '_')]
    if importance:
        topic_tags.append(importance.replace(' ', '_'))

    return [{
        'content':        content,
        'content_arabic': entry.get('arabic_text', '').strip() or None,
        'content_urdu':   None,
        'chunk_type':     'scientific',
        'token_count':    count_tokens(content),
        'stage_tags':     stage_tags,
        'topic_tags':     [t for t in topic_tags if t],
        'source_ref': {
            'id':               entry.get('id', ''),
            'reference':        entry.get('reference', ''),
            'scientific_field': sci_field,
            'evidence_strength': evidence_str,
            'importance':       importance,
        },
        'is_verified': False,   # alignment argument, not scripture itself
    }]


# ── 5. Comparative religion chunker ─────────────────────────────────────────

def chunk_comparative_topic(comparison: dict) -> list:
    """
    Parse one comparison object from Islam_comparison_with_Christianity_and_Judaism.json.

    Each comparison topic becomes ONE rich chunk containing:
      - topic + subtopics
      - Islamic position (core_belief + summary from islam_view)
      - key differences (list)
      - agreements (list)
      - dawah notes (common_ground_entry + key_islamic_argument)

    Input fields:
      comparison['id'], comparison['topic'], comparison['subtopics']
      comparison['stage']
      comparison['islam_view']['core_belief'], ['summary']
      comparison['christian_view']['core_belief']
      comparison['judaism_view']['core_belief']
      comparison['agreements']
      comparison['key_differences']
      comparison['dawah_notes']
      comparison['tone_instruction']
    """
    topic = comparison.get('topic', '')
    if not topic:
        return []

    islam_view    = comparison.get('islam_view', {})
    christian_view = comparison.get('christian_view', {})
    judaism_view  = comparison.get('judaism_view', {})
    dawah_notes   = comparison.get('dawah_notes', {})
    agreements    = comparison.get('agreements', [])
    differences   = comparison.get('key_differences', [])

    lines = [
        f'## Comparative Topic: {topic}',
        f'Subtopics: {", ".join(comparison.get("subtopics", []))}',
        '',
        '### Islamic Position',
        islam_view.get('core_belief', ''),
    ]

    if islam_view.get('summary'):
        lines.append(islam_view['summary'])

    if christian_view.get('core_belief'):
        lines.append('')
        lines.append('### Christian Position')
        lines.append(christian_view['core_belief'])

    if judaism_view.get('core_belief'):
        lines.append('')
        lines.append('### Jewish Position')
        lines.append(judaism_view['core_belief'])

    if agreements:
        lines.append('')
        lines.append('### Common Ground (All Three Traditions)')
        lines.extend([f'- {a}' for a in agreements])

    if differences:
        lines.append('')
        lines.append('### Key Differences')
        lines.extend([f'- {d}' for d in differences])

    if dawah_notes:
        lines.append('')
        lines.append('### Dawah Approach')
        if dawah_notes.get('common_ground_entry'):
            lines.append(dawah_notes['common_ground_entry'])
        if dawah_notes.get('key_islamic_argument'):
            lines.append(dawah_notes['key_islamic_argument'])

    content = '\n'.join(lines)
    stage_tags = normalise_stages(comparison.get('stage', [4]))

    return [{
        'content':        content,
        'content_arabic': None,
        'content_urdu':   None,
        'chunk_type':     'comparative',
        'token_count':    count_tokens(content),
        'stage_tags':     stage_tags,
        'topic_tags':     ['comparative_religion', 'interfaith',
                           comparison.get('id', '').replace('-', '_')],
        'source_ref': {
            'id':    comparison.get('id', ''),
            'topic': topic,
        },
        'is_verified': False,
    }]


# ── 6. Logic / reasoning framework chunker ───────────────────────────────────

def chunk_logic_entry(entry: dict, entry_type: str) -> list:
    """
    Parse one entry from reasoning_framework.json.
    entry_type: 'fallacy' | 'burden_of_proof' | 'debate_strategy'

    Each logical fallacy or strategy = one chunk.

    Input (for fallacy):
      entry['id'], entry['name'], entry['definition']
      entry['example'], entry['reframing_strategy']
      entry['usage_notes'], entry['debate_stage']

    Input (for other sections):
      entry['name'], entry['description'] or entry['explanation']
      entry['usage_notes'], entry['debate_stage'] (may be missing = all stages)
    """
    name       = entry.get('name', '')
    definition = (entry.get('definition') or entry.get('description')
                  or entry.get('explanation', ''))
    example    = entry.get('example', '')
    reframing  = entry.get('reframing_strategy', '')
    usage      = entry.get('usage_notes', '')

    if not name:
        return []

    lines = [f'## {name}', f'Type: {entry_type}', '']
    if definition:
        lines.append(f'Definition: {definition}')
    if example:
        lines.append(f'\nExample: {example}')
    if reframing:
        lines.append(f'\nReframing Strategy: {reframing}')
    if usage:
        lines.append(f'\nUsage: {usage}')

    content = '\n'.join(lines)

    raw_stages = entry.get('debate_stage', [1, 2, 3, 4])
    stage_tags = normalise_stages(raw_stages)

    return [{
        'content':        content,
        'content_arabic': None,
        'content_urdu':   None,
        'chunk_type':     'logic',
        'token_count':    count_tokens(content),
        'stage_tags':     stage_tags,
        'topic_tags':     ['logic', entry_type, entry.get('id', '').lower()],
        'source_ref': {
            'id':   entry.get('id', ''),
            'name': name,
            'type': entry_type,
        },
        'is_verified': False,
    }]


# ── 7. Meta chunker (debate_topics + glossary) ───────────────────────────────

def chunk_debate_topic(topic: dict, stage_str: str) -> list:
    """
    Parse one topic object from debate_topics.json.

    Each topic becomes one chunk with:
      - user_claim_examples (what atheists/skeptics say)
      - core_arguments (responses to use)
      - socratic_questions (follow-up questions)
    """
    topic_id = topic.get('topic_id', '')
    category = topic.get('category', '')
    claims   = topic.get('user_claim_examples', [])
    args     = topic.get('core_arguments', [])
    socratic = topic.get('socratic_questions', [])
    sources  = topic.get('supporting_sources', [])

    if not topic_id:
        return []

    lines = [
        f'## Debate Topic: {topic_id.replace("_", " ").title()}',
        f'Category: {category}',
        '',
    ]
    if claims:
        lines.append('### Common User Claims')
        lines.extend([f'- "{c}"' for c in claims])
    if args:
        lines.append('')
        lines.append('### Core Arguments to Present')
        lines.extend([f'- {a}' for a in args])
    if socratic:
        lines.append('')
        lines.append('### Socratic Questions to Ask')
        lines.extend([f'- {q}' for q in socratic])
    if sources:
        lines.append('')
        lines.append(f'Supporting Sources: {", ".join(sources)}')

    content = '\n'.join(lines)

    return [{
        'content':        content,
        'content_arabic': None,
        'content_urdu':   None,
        'chunk_type':     'meta',
        'token_count':    count_tokens(content),
        'stage_tags':     [stage_str],
        'topic_tags':     ['debate_topic', category, topic_id],
        'source_ref': {
            'topic_id':   topic_id,
            'category':   category,
            'transition': topic.get('transition_condition', ''),
        },
        'is_verified': False,
    }]


def chunk_glossary_term(term: str, definition_obj) -> list:
    """
    Parse one term from glossary.json core_concepts or philosophical_terms.
    definition_obj: either a dict (with 'definition', 'stage') or a plain string.
    """
    if isinstance(definition_obj, dict):
        definition = definition_obj.get('definition', '')
        stage_int  = definition_obj.get('stage', 1)
        stage_tags = normalise_stages([stage_int])
    else:
        definition = str(definition_obj)
        stage_tags = ['existence', 'prophethood', 'muhammad', 'invitation']

    if not definition:
        return []

    content = f'## {term}\nDefinition: {definition}'

    return [{
        'content':        content,
        'content_arabic': None,
        'content_urdu':   None,
        'chunk_type':     'meta',
        'token_count':    count_tokens(content),
        'stage_tags':     stage_tags,
        'topic_tags':     ['glossary', term.lower().replace(' ', '_')],
        'source_ref': {'term': term},
        'is_verified': False,
    }]
