# Authentication Setup Guide

## Backend Configuration Complete ✅

### Fixed Issues:
1. **User Model**: Email field now properly configured with default value
2. **Custom Serializers**: Created UserSerializer and UserRegistrationSerializer
3. **Google OAuth**: Added proper configuration in settings
4. **Token Authentication**: Configured DRF token authentication
5. **Email Verification**: Changed from mandatory to optional for better UX

### Environment Variables Required:
```bash
# Copy .env.example to .env and fill these:
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**Backend (.env):**
- `SECRET_KEY`: Django secret key
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth client secret
- Database credentials (DB_NAME, DB_USER, DB_PASSWORD, etc.)

**Frontend (.env):**
- `VITE_API_URL`: http://localhost:8000/api/v1
- `VITE_GOOGLE_CLIENT_ID`: Same Google OAuth client ID

## Frontend Configuration Complete ✅

### Fixed Issues:
1. **Token Management**: Added proper token storage and retrieval
2. **API Interceptors**: Added auth token to requests
3. **useAuth Hook**: Enhanced with proper error handling and token management
4. **App Component**: Fixed missing useAuth import

### Authentication Flows:

#### 1. Email Registration & Login
```
POST /api/v1/auth/registration/
Body: { email, password1, password2 }

POST /api/v1/auth/login/
Body: { email, password }
```

#### 2. Google OAuth
```
POST /api/v1/auth/social/google/
Body: { access_token: <google_token> }
```

## Setup Steps:

### 1. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:8000/api/v1/auth/social/google/`
   - `http://127.0.0.1:8000/api/v1/auth/social/google/`
6. Copy Client ID and Secret to .env files

### 2. Django Admin Setup
```bash
# Create superuser
python manage.py createsuperuser

# Configure Google OAuth in Django Admin
# Go to /admin/socialaccount/socialapp/
# Add a new SocialApp with:
# - Provider: Google
# - Client ID: your Google OAuth Client ID
# - Secret Key: your Google OAuth Client Secret
```

### 3. Database Migration
```bash
python manage.py migrate
```

### 4. Test Authentication
```bash
# Start backend
python manage.py runserver

# Start frontend (in separate terminal)
cd frontend
npm run dev
```

## API Endpoints:

### Authentication:
- `POST /api/v1/auth/login/` - Email login
- `POST /api/v1/auth/logout/` - Logout
- `POST /api/v1/auth/registration/` - Email registration
- `POST /api/v1/auth/social/google/` - Google OAuth
- `GET /api/v1/auth/user/` - Get current user

### Debate (requires auth):
- `POST /api/v1/debate/message/` - Send message
- `GET /api/v1/debate/sessions/` - Get sessions
- `GET /api/v1/debate/sessions/{id}/` - Get session details

## Security Features:
- ✅ Token-based authentication
- ✅ CSRF protection
- ✅ CORS configuration
- ✅ Rate limiting
- ✅ Password validation
- ✅ Email verification (optional)

## Testing:
1. **Email Registration**: Test with valid email and matching passwords
2. **Email Login**: Test with registered credentials
3. **Google OAuth**: Test with Google account
4. **Token Persistence**: Test login persists across page refresh
5. **Logout**: Test logout clears tokens and redirects

## Troubleshooting:
- **401 Errors**: Check token is being sent in Authorization header
- **CORS Issues**: Verify frontend URL in CORS_ALLOWED_ORIGINS
- **Google OAuth Failures**: Check client ID/secret and redirect URIs
- **Database Issues**: Run migrations and check database connection
