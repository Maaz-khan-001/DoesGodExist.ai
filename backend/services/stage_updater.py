import logging
from debate_app.models import DebateSession

logger = logging.getLogger(__name__)

NEGATION_PHRASES = [
    "don't", "dont", "do not", "doesn't", "not really", "not convinced",
    "not sure", "not accepting", "no longer", "changed my mind",
    "take that back", "actually no", "never mind", "i disagree",
    "still don't", "still not", "i reject", "that's not convincing",
    "not convinced by", "i'm not convinced", "im not convinced",
    "hard to believe", "i doubt", "skeptical", "unconvinced",
]

ACCEPTANCE_PHRASES = {
    'god_acceptance': [
        'i accept', 'you convinced me', 'god exists', 'i believe in god',
        'makes sense', 'i agree', 'that is convincing', 'that makes sense',
        'i can see that', 'you have a point', 'fair point', 'i concede',
        'hard to argue', 'cannot deny', "can't deny", 'i accept that',
        'i think god exists', 'god must exist', 'you have convinced me',
        'i am convinced', "i'm convinced", 'i now believe',
        'that argument convinced me',
    ],
    'prophecy_acceptance': [
        'prophets make sense', 'prophecy is reasonable', 'i accept prophets',
        'guidance makes sense', 'need for guidance', 'i accept prophecy',
        'i accept the concept of prophethood', 'prophethood is logical',
        'i believe in prophethood', 'you have convinced me about prophets',
        'makes sense that god would send guidance',
    ],
    'muhammad_acceptance': [
        'muhammad was a prophet', 'i accept muhammad', 'quran is divine',
        'quran could not be written by a human', 'quran is from god',
        'i accept the quran', 'quran is miraculous', 'muhammad pbuh was a prophet',
        'i believe muhammad was a prophet', 'the quran is authentic',
        'muhammad must have been a prophet',
    ],
}

STAGE_PROGRESSION = {
    'existence': 'prophethood',
    'prophethood': 'muhammad',
    'muhammad': 'invitation',
}

# FIX: Minimum turns before stage advancement (prevents rushing through stages)
MIN_TURNS_FOR_ADVANCEMENT = 3


class StageUpdater:
    def apply(self, session: DebateSession, user_message: str) -> bool:
        msg_lower = user_message.lower()

        # Negation guard
        if any(phrase in msg_lower for phrase in NEGATION_PHRASES):
            return False

        # FIX: Only advance ONE flag per message (prevents skipping stages)
        # Process in stage order: god → prophecy → muhammad
        for flag, phrases in ACCEPTANCE_PHRASES.items():
            if getattr(session, flag) is not True:
                if any(phrase in msg_lower for phrase in phrases):
                    # FIX: Check minimum turn count before allowing advancement
                    if session.total_turns < MIN_TURNS_FOR_ADVANCEMENT:
                        logger.info(
                            f'Stage advancement blocked — only {session.total_turns} turns '
                            f'(minimum {MIN_TURNS_FOR_ADVANCEMENT} required)'
                        )
                        return False

                    setattr(session, flag, True)
                    session.save(update_fields=[flag])
                    logger.info(f'Stage flag set: {flag}=True for session {session.id}')

                    # Try to advance to next stage
                    return self._try_advance(session)

        return False

    def _try_advance(self, session: DebateSession) -> bool:
        next_stage = STAGE_PROGRESSION.get(session.current_stage)
        if not next_stage:
            return False

        from services.stage_validator import StageGateValidator, StageNotUnlocked

        original = session.current_stage
        session.current_stage = next_stage
        try:
            StageGateValidator().validate(session)
            session.save(update_fields=['current_stage'])
            logger.info(
                f'Stage advanced: {original} → {next_stage} for session {session.id}'
            )
            return True
        except StageNotUnlocked:
            session.current_stage = original
            return False
