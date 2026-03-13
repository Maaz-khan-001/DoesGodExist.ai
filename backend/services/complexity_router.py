import logging
import re
from debate_app.models import DebateSession

logger = logging.getLogger(__name__)

# Keywords/patterns that indicate a complex message requiring GPT-4o
COMPLEXITY_TRIGGERS = [
    # Philosophical terms
    'ontological', 'cosmological', 'teleological', 'epistemology',
    'metaphysical', 'a priori', 'a posteriori', 'contingent being',
    'necessary being', 'modal logic', 'syllogism', 'deductive',
    'inductive', 'fallacy', 'premise', 'axiomatic', 'kalam',

    # Scientific / technical
    'quantum mechanics', 'thermodynamics', 'entropy', 'fine-tuning',
    'anthropic principle', 'multiverse', 'string theory',
    'cosmological constant', 'higgs boson', 'nucleosynthesis',

    # Comparative religion / historical
    'textual criticism', 'manuscript', 'isnad', 'hermeneutics',
    'exegesis', 'tafsir', 'ijaz', 'mutawatir',

    # Complex debate patterns
    'prove that', 'argument for', 'argument against', 'counter-argument',
    'logical contradiction', 'paradox', 'refute', 'rebut',
]

# Simple patterns → cheaper model
SIMPLE_TRIGGERS = [
    'what is', "what's", 'who is', 'tell me about', 'explain',
    'hi', 'hello', 'thanks', 'thank you', 'ok', 'okay',
    'i see', 'interesting', 'got it', 'makes sense',
]

# Always use GPT-4o after a certain number of turns (deep conversations)
DEPTH_THRESHOLD_FOR_4O = 8


class ComplexityRouter:
    """
    Routes debate messages to the appropriate GPT model based on complexity.

    GPT-4o-mini: Simple questions, factual queries, conversational responses.
    GPT-4o:      Complex philosophical/scientific arguments, long messages,
                 late-stage debates, messages with technical terminology.

    Cost impact:
      GPT-4o is ~33x more expensive than GPT-4o-mini per token.
      Routing simple messages to mini saves ~85% of API costs.
    """

    def route(
        self,
        message: str,
        session: DebateSession,
        current_seq: int = 0,
    ) -> tuple[str, str]:
        """
        Returns (model_name, routing_reason).

        Args:
          message:     The user's message text
          session:     The current debate session
          current_seq: The sequence number of the current user message
        """
        msg_lower = message.lower()
        word_count = len(message.split())

        # Rule 1: Very long messages → GPT-4o (user is engaged/serious)
        if word_count > 80:
            return 'gpt-4o', 'long_message'

        # Rule 2: Contains complex terminology → GPT-4o
        for trigger in COMPLEXITY_TRIGGERS:
            if trigger in msg_lower:
                return 'gpt-4o', f'complex_term:{trigger}'

        # Rule 3: Deep into conversation → GPT-4o (maintain quality)
        if current_seq >= DEPTH_THRESHOLD_FOR_4O * 2:
            return 'gpt-4o', 'conversation_depth'

        # Rule 4: Invitation stage → GPT-4o (most important stage)
        if session.current_stage == 'invitation':
            return 'gpt-4o', 'invitation_stage'

        # Rule 5: Short simple message → GPT-4o-mini
        if word_count < 15:
            for simple in SIMPLE_TRIGGERS:
                if simple in msg_lower:
                    return 'gpt-4o-mini', 'simple_message'

        # Default: mini
        return 'gpt-4o-mini', 'default'
