

from django.urls import path
from .views import DebateMessageView, DebateSessionListView, DebateSessionDetailView
from .views_stream import DebateStreamView

urlpatterns = [
    path('message/', DebateMessageView.as_view(), name='debate-message'),
    path('sessions/', DebateSessionListView.as_view(), name='session-list'),
    path('sessions/<uuid:pk>/', DebateSessionDetailView.as_view(), name='session-detail'),
    # DELETE /api/v1/debate/sessions/<uuid:pk>/ is handled by the same view
    # (the view has both get() and delete() methods)
    path('message/stream/', DebateStreamView.as_view(), name='debate-message-stream'),
]





