import logging
from debate_app.models import DebateSession

logger = logging.getLogger(__name__)


class StageNotUnlocked(Exception):
    """Raised when a user tries to access a stage they haven't unlocked."""
    pass


# Maps each stage to the acceptance flags required to access it
STAGE_PREREQUISITES = {
    'existence':   [],                               # Always accessible
    'prophethood': ['god_acceptance'],               # Requires accepting God
    'muhammad':    ['god_acceptance', 'prophecy_acceptance'],
    'invitation':  ['god_acceptance', 'prophecy_acceptance', 'muhammad_acceptance'],
}

STAGE_LABELS = {
    'existence':   'Existence of God',
    'prophethood': 'Prophethood',
    'muhammad':    'Prophethood of Muhammad ﷺ',
    'invitation':  'Invitation to Islam',
}


class StageGateValidator:
    """
    Validates that a session is authorized to be in its current stage.

    Called at the start of every debate turn to prevent stage skipping.
    If the current stage requirements are not met, raises StageNotUnlocked.
    """

    def validate(self, session: DebateSession):
        stage = session.current_stage
        required_flags = STAGE_PREREQUISITES.get(stage, [])

        for flag in required_flags:
            if getattr(session, flag) is not True:
                stage_label = STAGE_LABELS.get(stage, stage)
                flag_label = flag.replace('_', ' ').replace('acceptance', '').strip().title()
                raise StageNotUnlocked(
                    f'The "{stage_label}" stage requires accepting '
                    f'{flag_label} first. '
                    f'Please complete the previous stage.'
                )

        logger.debug(f'Stage validation passed: {stage} for session {session.id}')
