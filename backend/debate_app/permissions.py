from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: only the owner of an object can modify it.
    Assumes the object has a `user` attribute.

    Used on:
      - DebateSession detail/delete endpoints
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user


class IsSessionOwner(BasePermission):
    """
    Object-level permission: user must own the DebateSession.
    Returns 404-style 403 (not leaking whether the object exists).

    Stricter than IsOwnerOrReadOnly — blocks even GET if not owner.
    Used on session detail, delete, and full history endpoints.
    """
    message = 'You do not have permission to access this session.'

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdminUserOrReadOnly(BasePermission):
    """
    Admin users have full access.
    Authenticated non-admin users have read-only access.
    Anonymous users have no access.

    Used on: PromptTemplate management endpoints.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff


class IsAnonymousOrAuthenticated(BasePermission):
    """
    Allows both anonymous (tracked by session) and authenticated users.
    This is the permissive permission used on the main debate endpoint.

    Anonymous users are allowed but their session_key must be tracked.
    """
    def has_permission(self, request, view):
        # Always allow — rate limiting is handled separately
        return True


class IsPremiumUser(BasePermission):
    """
    Only allows users with tier='premium'.
    Used on premium features (unlimited turns, streaming, etc.)
    """
    message = 'This feature requires a premium account.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.tier == 'premium'
