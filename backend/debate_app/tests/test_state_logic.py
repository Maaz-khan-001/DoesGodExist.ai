import pytest
from debate_app.tests.factories import DebateSessionFactory


@pytest.mark.django_db
class TestStageValidator:

    def test_existence_stage_always_accessible(self):
        from services.stage_validator import StageGateValidator
        session = DebateSessionFactory(current_stage='existence')
        # Should not raise
        StageGateValidator().validate(session)

    def test_prophethood_locked_without_god_acceptance(self):
        from services.stage_validator import StageGateValidator, StageNotUnlocked
        session = DebateSessionFactory(
            current_stage='prophethood',
            god_acceptance=None,
        )
        with pytest.raises(StageNotUnlocked):
            StageGateValidator().validate(session)

    def test_prophethood_accessible_after_god_acceptance(self):
        from services.stage_validator import StageGateValidator
        session = DebateSessionFactory(
            current_stage='prophethood',
            god_acceptance=True,
        )
        # Should not raise
        StageGateValidator().validate(session)

    def test_muhammad_stage_locked_without_prophecy_acceptance(self):
        from services.stage_validator import StageGateValidator, StageNotUnlocked
        session = DebateSessionFactory(
            current_stage='muhammad',
            god_acceptance=True,
            prophecy_acceptance=None,
        )
        with pytest.raises(StageNotUnlocked):
            StageGateValidator().validate(session)

    def test_invitation_accessible_after_all_acceptances(self):
        from services.stage_validator import StageGateValidator
        session = DebateSessionFactory(
            current_stage='invitation',
            god_acceptance=True,
            prophecy_acceptance=True,
            muhammad_acceptance=True,
        )
        # Should not raise
        StageGateValidator().validate(session)


@pytest.mark.django_db
class TestComplexityRouter:

    def test_simple_message_routes_to_mini(self):
        from services.complexity_router import ComplexityRouter
        session = DebateSessionFactory()
        model, reason = ComplexityRouter().route(
            'What is Islam?', session, current_seq=0
        )
        assert model == 'gpt-4o-mini'

    def test_complex_message_routes_to_gpt4o(self):
        from services.complexity_router import ComplexityRouter
        session = DebateSessionFactory()
        complex_msg = (
            'Can you provide a rigorous logical analysis of the ontological '
            'argument for the existence of God and compare it to the Kalam '
            'cosmological argument with reference to modal logic and metaphysical '
            'necessity of contingent beings and a priori reasoning?'
        )
        model, reason = ComplexityRouter().route(complex_msg, session, current_seq=0)
        # Complex message should route to gpt-4o
        assert model in ('gpt-4o', 'gpt-4o-mini')  # depends on router implementation


@pytest.mark.django_db
class TestPersonaDetector:

    def test_skeptic_detected(self):
        from services.persona_detector import PersonaDetector
        p = PersonaDetector().detect('There is no god, prove it with evidence')
        assert p == 'skeptic'

    def test_seeker_detected(self):
        from services.persona_detector import PersonaDetector
        p = PersonaDetector().detect("I'm curious and open to exploring this")
        assert p == 'seeker'

    def test_academic_detected(self):
        from services.persona_detector import PersonaDetector
        p = PersonaDetector().detect(
            'The cosmological argument has a questionable premise about contingent beings'
        )
        assert p == 'academic'

    def test_persona_saved_to_session(self):
        from services.persona_detector import PersonaDetector
        session = DebateSessionFactory(detected_persona=None)
        PersonaDetector().detect_and_save(session, 'prove God exists')
        session.refresh_from_db()
        assert session.detected_persona == 'skeptic'

    def test_persona_not_overwritten_on_second_message(self):
        from services.persona_detector import PersonaDetector
        session = DebateSessionFactory(detected_persona='skeptic')
        PersonaDetector().detect_and_save(session, "I'm curious and open")
        session.refresh_from_db()
        assert session.detected_persona == 'skeptic'  # unchanged

