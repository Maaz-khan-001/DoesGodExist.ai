"""
Django Admin Test Suite

Tests for all admin configurations across all apps.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from uuid import uuid4

User = get_user_model()


class BaseAdminTestCase(TestCase):
    """Base test case for admin functionality."""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        self.client.login(username='admin@example.com', password='testpass123')


class DebateAppAdminTests(BaseAdminTestCase):
    """Tests for debate_app admin functionality."""
    
    def test_user_admin_list_view(self):
        """Test User admin list view loads and displays users."""
        response = self.client.get(reverse('admin:debate_app_user_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin@example.com')
        self.assertContains(response, 'user@example.com')
    
    def test_user_admin_add_view(self):
        """Test User admin add view."""
        response = self.client.get(reverse('admin:debate_app_user_add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')
    
    def test_debate_session_admin_list_view(self):
        """Test DebateSession admin list view."""
        from debate_app.models import DebateSession
        
        # Create a test session
        session = DebateSession.objects.create(
            user=self.admin_user,
            current_stage='existence',
            debate_mode='standard'
        )
        
        response = self.client.get(reverse('admin:debate_app_debatesession_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(session.id))
    
    def test_message_admin_list_view(self):
        """Test Message admin list view."""
        from debate_app.models import DebateSession, Message
        
        # Create test session and message
        session = DebateSession.objects.create(user=self.admin_user)
        message = Message.objects.create(
            session=session,
            role='user',
            content='Test message',
            stage='existence',
            sequence_num=1
        )
        
        response = self.client.get(reverse('admin:debate_app_message_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test message')
    
    def test_prompt_template_admin_list_view(self):
        """Test PromptTemplate admin list view."""
        from debate_app.models import PromptTemplate
        
        template = PromptTemplate.objects.create(
            stage='existence',
            version=1,
            system_template='Test system template',
            context_template='Test context template',
            tone='logical'
        )
        
        response = self.client.get(reverse('admin:debate_app_prompttemplate_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'existence')


class AnalyticsAppAdminTests(BaseAdminTestCase):
    """Tests for analytics_app admin functionality."""
    
    def test_gpt_log_admin_list_view(self):
        """Test GPTLog admin list view."""
        from analytics_app.models import GPTLog
        from debate_app.models import DebateSession, Message
        
        # Create test data
        session = DebateSession.objects.create(user=self.admin_user)
        message = Message.objects.create(
            session=session,
            role='user',
            content='Test',
            stage='existence',
            sequence_num=1
        )
        
        log = GPTLog.objects.create(
            session=session,
            message=message,
            model_used='gpt-4',
            routing_reason='test',
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost_usd=0.001,
            latency_ms=500
        )
        
        response = self.client.get(reverse('admin:analytics_app_gptlog_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gpt-4')
    
    def test_budget_alert_admin_list_view(self):
        """Test BudgetAlert admin list view."""
        from analytics_app.models import BudgetAlert
        from datetime import date
        
        alert = BudgetAlert.objects.create(
            month=date.today(),
            total_cost_usd=100.00,
            alert_level='50pct'
        )
        
        response = self.client.get(reverse('admin:analytics_app_budgetalert_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50pct')


class RagAppAdminTests(BaseAdminTestCase):
    """Tests for rag_app admin functionality."""
    
    def test_document_admin_list_view(self):
        """Test Document admin list view."""
        from rag_app.models import Document
        
        doc = Document.objects.create(
            title='Test Document',
            source_type='quran',
            author='Test Author',
            checksum='test_checksum_123',
            indexing_status='pending'
        )
        
        response = self.client.get(reverse('admin:rag_app_document_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Document')
        self.assertContains(response, 'quran')
    
    def test_document_chunk_admin_list_view(self):
        """Test DocumentChunk admin list view."""
        from rag_app.models import Document, DocumentChunk
        
        doc = Document.objects.create(
            title='Test Document',
            source_type='quran',
            checksum='test_checksum_123'
        )
        
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content='Test content',
            token_count=10,
            chunk_type='verse'
        )
        
        response = self.client.get(reverse('admin:rag_app_documentchunk_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test content')


class AdminAccessTests(BaseAdminTestCase):
    """Tests for admin access control."""
    
    def test_non_staff_user_cannot_access_admin(self):
        """Test that non-staff users cannot access admin."""
        self.client.logout()
        self.client.login(username='user@example.com', password='testpass123')
        
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_unauthenticated_user_cannot_access_admin(self):
        """Test that unauthenticated users cannot access admin."""
        self.client.logout()
        
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_staff_user_can_access_admin(self):
        """Test that staff users can access admin."""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')


class AdminIntegrationTests(BaseAdminTestCase):
    """Integration tests for admin functionality."""
    
    def test_admin_search_functionality(self):
        """Test admin search functionality."""
        from debate_app.models import DebateSession
        
        # Create test data
        session = DebateSession.objects.create(
            user=self.admin_user,
            current_stage='existence'
        )
        
        # Test search
        response = self.client.get(
            reverse('admin:debate_app_debatesession_changelist') + f'?q={session.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(session.id))
    
    def test_admin_filter_functionality(self):
        """Test admin filter functionality."""
        from debate_app.models import DebateSession
        
        # Create test data with different stages
        DebateSession.objects.create(user=self.admin_user, current_stage='existence')
        DebateSession.objects.create(user=self.admin_user, current_stage='prophethood')
        
        # Test filter
        response = self.client.get(
            reverse('admin:debate_app_debatesession_changelist') + '?current_stage=existence'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'existence')
