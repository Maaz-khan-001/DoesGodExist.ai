from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView


class GoogleLogin(SocialLoginView):
    """
    POST /api/v1/auth/social/google/
    Body: { "access_token": "<token from @react-oauth/google>" }
    """
    adapter_class = GoogleOAuth2Adapter


def api_root(request):
    from django.urls import reverse
    return JsonResponse({
        'message': 'DoesGodExist.ai API',
        'version': 'v1',
        'endpoints': {
            'auth': '/api/v1/auth/',
            'debate': '/api/v1/debate/',
            'analytics': '/api/v1/analytics/',
            'social_google': '/api/v1/auth/social/google/',
            'admin': '/admin/',
        }
    })


urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),

    # Debate API
    path('api/v1/debate/', include('debate_app.urls')),

    # Analytics API (new)
    path('api/v1/analytics/', include('analytics_app.urls')),

    # dj-rest-auth: login, logout, user, password reset
    path('api/v1/auth/', include('dj_rest_auth.urls')),

    # dj-rest-auth registration + email verification
    path('api/v1/auth/registration/', include('dj_rest_auth.registration.urls')),

    # Google social login
    path('api/v1/auth/social/google/', GoogleLogin.as_view(), name='google-login'),

    # JWT token refresh endpoint
    path('api/v1/auth/token/refresh/',
         __import__('rest_framework_simplejwt.views', fromlist=['TokenRefreshView']).TokenRefreshView.as_view(),
         name='token-refresh'),

    # allauth URLs (required for OAuth callback)
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)



