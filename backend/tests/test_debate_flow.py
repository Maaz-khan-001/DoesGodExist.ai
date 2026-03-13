"""
Full end-to-end debate flow tests.

These tests exercise the complete path:
  HTTP request → View → Orchestrator → GPT (mocked) → DB → Response

They test that all components work together correctly, not just in isolation.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from debate_app.tests.factories import UserFactory, DebateSessionFactory
from debate_app.models import DebateSession, Message


def _gpt_response_mock(content='This is a test AI response about God.'):
    """Create a GPTResponse-like mock object."""
    from services.gpt_client import GPTResponse
    return GPTResponse(
        content=content,
        model='gpt-4o-mini',
        prompt_tokens=150,
        completion_tokens=60,
        cost_usd=0.00003,
        latency_ms=700,
    )


@pytest.mark.system
@pytest.mark.django_db(transaction=True)
class TestFullDebateFlow:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/debate/message/'

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_first_message_creates_session_and_messages(
        self, mock_retrieve, mock_gpt
    ):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        user = UserFactory()
        self.client.force_authenticate(user=user)

        resp = self.client.post(self.url, {
            'message': 'Does God exist?',
        }, format='json')

        assert resp.status_code == 200

        # Session created
        session_id = resp.data['session_id']
        session = DebateSession.objects.get(id=session_id)
        assert session.user == user
        assert session.current_stage == 'existence'
        assert session.total_turns == 1

        # Both messages saved
        msgs = list(session.messages.order_by('sequence_num'))
        assert len(msgs) == 2
        assert msgs[0].role == 'user'
        assert msgs[0].content == 'Does God exist?'
        assert msgs[1].role == 'assistant'
        assert msgs[1].content == 'This is a test AI response about God.'

        # Sequence numbers are correct
        assert msgs[0].sequence_num == 0
        assert msgs[1].sequence_num == 1

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_persona_detected_on_first_message(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        user = UserFactory()
        self.client.force_authenticate(user=user)

        resp = self.client.post(self.url, {
            'message': 'There is no God, prove it with evidence please',
        }, format='json')

        assert resp.status_code == 200
        assert resp.data['persona'] == 'skeptic'

        session = DebateSession.objects.get(id=resp.data['session_id'])
        assert session.detected_persona == 'skeptic'

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_stage_advances_on_acceptance(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        user = UserFactory()
        session = DebateSessionFactory(
            user=user,
            current_stage='existence',
            total_turns=5,  # Past minimum turn threshold
        )
        self.client.force_authenticate(user=user)

        resp = self.client.post(self.url, {
            'message': 'You have convinced me — I believe God exists now.',
            'session_id': str(session.id),
        }, format='json')

        assert resp.status_code == 200
        assert resp.data['stage_advanced'] is True
        assert resp.data['stage'] == 'prophethood'

        session.refresh_from_db()
        assert session.current_stage == 'prophethood'
        assert session.god_acceptance is True

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_cost_and_tokens_accumulated_atomically(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        user = UserFactory()
        session = DebateSessionFactory(user=user)
        self.client.force_authenticate(user=user)

        # Send 3 messages
        for i in range(3):
            self.client.post(self.url, {
                'message': f'Question {i}',
                'session_id': str(session.id),
            }, format='json')

        session.refresh_from_db()
        assert session.total_turns == 3
        # Cost should be 3 × 0.00003 = 0.00009
        assert float(session.total_cost_usd) == pytest.approx(0.00009, abs=1e-7)

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_second_message_in_same_session(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock('Second response')

        user = UserFactory()
        self.client.force_authenticate(user=user)

        # First message
        resp1 = self.client.post(self.url, {
            'message': 'First question',
        }, format='json')
        session_id = resp1.data['session_id']

        # Second message in same session
        resp2 = self.client.post(self.url, {
            'message': 'Follow-up question',
            'session_id': session_id,
        }, format='json')

        assert resp2.status_code == 200
        assert resp2.data['session_id'] == session_id  # Same session

        session = DebateSession.objects.get(id=session_id)
        assert session.messages.count() == 4  # 2 user + 2 assistant

    @patch('services.orchestrator.DebateOrchestrator.run')
    def test_budget_cutoff_returns_503(self, mock_run):
        from services.orchestrator import BudgetCutoffActive
        mock_run.side_effect = BudgetCutoffActive()

        user = UserFactory()
        self.client.force_authenticate(user=user)

        resp = self.client.post(self.url, {
            'message': 'Test during cutoff',
        }, format='json')

        assert resp.status_code == 503
        assert resp.data['code'] == 'BUDGET_CUTOFF'

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_session_history_accessible_after_debate(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        user = UserFactory()
        self.client.force_authenticate(user=user)

        # Start a debate
        resp = self.client.post(self.url, {'message': 'Test'}, format='json')
        session_id = resp.data['session_id']

        # Get session list
        list_resp = self.client.get('/api/v1/debate/sessions/')
        assert list_resp.status_code == 200
        assert len(list_resp.data) == 1

        # Get session detail with messages
        detail_resp = self.client.get(f'/api/v1/debate/sessions/{session_id}/')
        assert detail_resp.status_code == 200
        assert len(detail_resp.data['messages']) == 2

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_anonymous_user_full_flow(self, mock_retrieve, mock_gpt):
        mock_retrieve.return_value = []
        mock_gpt.return_value = _gpt_response_mock()

        # No authentication
        resp = self.client.post(self.url, {
            'message': 'What is Islam?',
        }, format='json')

        assert resp.status_code == 200
        assert resp.data['session_id'] is not None

        # Session created for anonymous user
        session = DebateSession.objects.get(id=resp.data['session_id'])
        assert session.user.is_anonymous_user is True


@pytest.mark.system
@pytest.mark.django_db(transaction=True)
class TestConcurrentRequestSafety:
    """
    Tests that race conditions are prevented under concurrent requests.
    Simulates concurrent requests using threading.
    """

    def test_sequence_numbers_unique_under_concurrency(self):
        """
        FIX 1: unittest.mock.patch is NOT thread-safe — patches applied via
        @patch decorator only affect the calling thread. Worker threads see
        the real (unpatched) implementations and hit real services → 500.
        Solution: use patch() as context manager BEFORE spawning threads.

        FIX 2: Django's test DB uses a single connection per thread by default.
        With transaction=True, threads must call close_old_connections() before
        using the DB, otherwise they share/clobber each other's connections.
        Solution: call django.db.close_old_connections() at the start of each thread.

        FIX 3: select_for_update() causes threads to queue, not deadlock.
        Some may get 429 (turn limit) or 200 — both are acceptable outcomes.
        """
        import threading
        from django.db import close_old_connections
        from services.gpt_client import GPTResponse

        user = UserFactory()
        session = DebateSessionFactory(user=user)
        errors = []

        with patch('rag_app.retrieval_service.RetrievalService.retrieve',
                   return_value=[]), \
             patch('services.gpt_client.GPTClient.complete',
                   return_value=GPTResponse(
                       content='Test response',
                       model='gpt-4o-mini',
                       prompt_tokens=10,
                       completion_tokens=5,
                       cost_usd=0.000001,
                       latency_ms=100,
                   )):

            def send_message(n):
                # Each thread needs its own fresh DB connection
                close_old_connections()
                client = APIClient()
                client.force_authenticate(user=user)
                try:
                    resp = client.post(
                        '/api/v1/debate/message/',
                        {'message': f'Concurrent message {n}',
                         'session_id': str(session.id)},
                        format='json'
                    )
                    if resp.status_code not in (200, 429):
                        errors.append(
                            f'Unexpected status: {resp.status_code} — {resp.data}'
                        )
                except Exception as e:
                    errors.append(str(e))
                finally:
                    close_old_connections()

            threads = [threading.Thread(target=send_message, args=(i,))
                       for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert not errors, f'Errors during concurrent requests: {errors}'

        # No duplicate sequence numbers
        seqs = list(session.messages.values_list('sequence_num', flat=True))
        assert len(seqs) == len(set(seqs)), \
            f'Duplicate sequence numbers found: {seqs}'