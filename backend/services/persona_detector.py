import logging
from debate_app.models import DebateSession

logger = logging.getLogger(__name__)

SKEPTIC_KEYWORDS = [
    "don't believe", "no evidence", "prove it", "prove god", "religion is",
    "science says", "evolution", "big bang", "random", "naturalistic",
    "burden of proof", "there is no god", "atheist", "atheism",
    "not real", "superstition", "fairy tale", "mythology", "delusion",
    "wishful thinking", "no proof", "no scientific", "unproven",
]

SEEKER_KEYWORDS = [
    "not sure", "curious", "seeking", "wondering", "open to", "maybe",
    "what if", "searching", "looking for meaning", "want to understand",
    "something out there", "spiritual", "inner peace", "explore",
    "trying to understand", "interested in", "want to know", "can you explain",
    "tell me about", "help me understand",
]

ACADEMIC_KEYWORDS = [
    "argue", "premise", "conclusion", "logical", "fallacy", "philosophy",
    "epistemology", "ontology", "teleological", "kalam", "syllogism",
    "peer-reviewed", "empirically", "axiom", "deductive", "inductive",
    "cosmological", "metaphysical", "inference", "modal logic",
    "a priori", "a posteriori", "contingent", "necessary being",
]

# Minimum keyword hits to classify as each persona
THRESHOLDS = {
    'academic': 2,
    'seeker': 1,
}


class PersonaDetector:
    def detect(self, message: str) -> str:
        msg_lower = message.lower()
        academic_hits = sum(1 for kw in ACADEMIC_KEYWORDS if kw in msg_lower)
        skeptic_hits = sum(1 for kw in SKEPTIC_KEYWORDS if kw in msg_lower)
        seeker_hits = sum(1 for kw in SEEKER_KEYWORDS if kw in msg_lower)

        if academic_hits >= THRESHOLDS['academic']:
            return 'academic'
        if seeker_hits >= THRESHOLDS['seeker'] and skeptic_hits == 0:
            return 'seeker'
        return 'skeptic'  # Default: treat as skeptic (most challenging)

    def detect_and_save(self, session: DebateSession, message: str) -> str:
        """
        Detect persona from message and save to session IF not already set.
        Persona is set once on the first message and never changed.
        Returns the current persona string.
        """
        if session.detected_persona:
            return session.detected_persona  # Already set — don't override

        persona = self.detect(message)
        session.detected_persona = persona

        # Use update() to avoid overwriting other fields
        DebateSession.objects.filter(pk=session.pk).update(
            detected_persona=persona
        )
        logger.info(f'Persona detected: {persona} for session {session.id}')
        return persona
