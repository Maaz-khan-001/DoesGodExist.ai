import logging
from debate_app.models import PromptTemplate, DebateSession

logger = logging.getLogger(__name__)

PERSONA_INSTRUCTIONS = {
    'skeptic': (
        'The user is a skeptic. They require empirical evidence and logical arguments. '
        'Acknowledge their skepticism as intellectually honest. '
        'Avoid emotional appeals — use reason, science, and philosophy.'
    ),
    'seeker': (
        'The user is a genuine seeker. Be warm, open, and exploratory. '
        'Do not overwhelm with arguments. Invite reflection and inner exploration. '
        'Create space for the user to process what they are feeling.'
    ),
    'academic': (
        'The user has an academic mindset. Use formal logical structure. '
        'Reference philosophical frameworks (Kalam cosmological, Teleological, Ontological). '
        'Engage at peer level. Welcome intellectual challenge.'
    ),
    None: (
        'Engage with scholarly respect and logical clarity. '
        'Adapt your tone based on how the user responds.'
    ),
}

MODE_STYLE_MAP = {
    'standard':         'Present Quranic verses with scientific miracles and rational arguments.',
    'scientific':       'Focus on empirical evidence and cosmological/fine-tuning arguments.',
    'philosophical':    'Use formal logical structure. Socratic method encouraged.',
    'reflective':       'Open, exploratory tone. Invite inner reflection and personal inquiry.',
    'comparative':      'Compare Islam, Christianity, Judaism using historical and textual evidence.',
    'prophethood_mode': 'Focus on historical and moral evidence for prophethood.',
}

FORMATTING_SUFFIX = """

RESPONSE FORMAT:
- Begin with a clear heading (## Heading)
- Use emoji labels: 🧠 rational  🔬 scientific  📖 Quranic  ⚖️ comparative  💭 reflection
- Use markdown tables for side-by-side comparisons
- Wrap Arabic text in backticks: `بِسْمِ اللَّهِ`
- End EVERY response with:
  ## 💭 Reflection
  [One thoughtful follow-up question]

STRICT RULES:
- NEVER cite sources not present in [CONTEXT] below
- NEVER fabricate verse numbers or hadith numbers
- Label logical fallacies if detected (e.g., "This appears to be an ad hominem...")
- Never discuss politics or sectarian disputes within Islam
- Maintain scholarly, respectful tone regardless of user's attitude
"""

STAGE_LABELS = {
    'existence': 'Existence of God',
    'prophethood': 'Necessity of Prophethood',
    'muhammad': 'Prophethood of Muhammad ﷺ',
    'invitation': 'Invitation to Islam',
}


class PromptBuilder:
    def build(self, session: DebateSession, user_message: str, chunks, history):
        system = self._get_system(session)
        context = self._build_context(chunks)
        hist_text = self._build_history(history)

        user_with_ctx = (
            f'{hist_text}\n\n'
            f'[CONTEXT — Cite ONLY from these sources]\n'
            f'{context}\n'
            f'[/CONTEXT]\n\n'
            f'User: {user_message}'
        )
        return {'system': system, 'user': user_with_ctx}

    def _get_system(self, session: DebateSession) -> str:
        # FIX: Use filter().first() to avoid MultipleObjectsReturned
        template = PromptTemplate.objects.filter(
            stage=session.current_stage,
            is_active=True
        ).order_by('-version').first()

        if template:
            return template.system_template

        # Fallback: build system prompt from session state
        mode = MODE_STYLE_MAP.get(session.debate_mode, '')
        label = STAGE_LABELS.get(session.current_stage, session.current_stage)
        persona = session.detected_persona

        # FIX: Include persona instructions explicitly in system prompt
        persona_text = PERSONA_INSTRUCTIONS.get(persona, PERSONA_INSTRUCTIONS[None])

        return (
            f'You are DoesGodExist.ai — a calm, scholarly Islamic debate partner.\n\n'
            f'CURRENT STAGE: {label}\n'
            f'DEBATE MODE: {mode}\n'
            f'USER PERSONA: {persona or "unknown"}\n\n'
            f'PERSONA GUIDANCE:\n{persona_text}\n'
            f'{FORMATTING_SUFFIX}'
        )

    def _build_context(self, chunks, max_tokens=2500) -> str:
        lines, used = [], 0
        for i, c in enumerate(chunks, 1):
            if used + c.token_count + 30 > max_tokens:
                break
            ref = self._format_ref(c)
            entry = f'Source {i} ({ref}):\n{c.content}'
            if c.content_arabic:
                entry += f'\nArabic: `{c.content_arabic}`'
            lines.append(entry)
            used += c.token_count
        return '\n\n'.join(lines) if lines else 'No relevant context found.'

    def _format_ref(self, c) -> str:
        r = c.source_ref
        if c.chunk_type == 'quran':
            return f"Quran {r.get('surah')}:{r.get('ayah')} [Verified]"
        if c.chunk_type == 'hadith':
            return f"{r.get('collection')} #{r.get('number')}, Grade: {r.get('grade')}"
        return c.chunk_type.title()

    def _build_history(self, history, max_tokens=800) -> str:
        """
        FIX: Increased token budget from 600 to 800 words.
        Truncates individual messages at 400 chars (was 300).
        """
        lines, used = [], 0
        for msg in history:
            line = f'{msg.role.title()}: {msg.content[:400]}'
            words = len(line.split())
            if used + words > max_tokens:
                break
            lines.append(line)
            used += words
        return '\n'.join(lines)