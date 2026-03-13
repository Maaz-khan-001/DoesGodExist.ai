================================================================================
   DOESGODEXIST.AI — COMPLETE ARCHITECTURE GUIDE
   File 1 of 3 | Architecture v3.0 | Solo Founder Edition | Budget: $100–300/month
   Role: CTO + Lead Architect + UI/UX Advisor
================================================================================

CHANGELOG v3.0 (fixes applied vs v2.0):
  - DEBATE_CUTOFF_ACTIVE moved from process memory to Redis (fixes Gunicorn/Celery split-brain)
  - is_anonymous renamed to is_anonymous_user throughout (fixes Django built-in property conflict)
  - detected_persona detection service added to architecture (was missing entirely)
  - Session ownership enforcement added to DebateMessageView description
  - stage_advanced logic clarified (semantically correct now)
  - DATABASE_URL removed from .env; only individual DB_ vars are used (settings.py never read DATABASE_URL)
  - Celery Beat scheduler strategy clarified (dict-based, not DB-based)
  - STATICFILES_STORAGE updated to Django 4.2+ STORAGES format
  - Philosophy data loading added to deployment flow
  - Comparative scripture pipeline described (was entirely absent)
  - content_urdu population added to indexing pipeline description
  - Apple OAuth removed (never implemented; listed only for future reference)
  - ScriptureModal, AuthPage, SettingsPage, useAuth marked as Phase 2 features
  - React Router wiring added to frontend architecture
  - SURAH_STAGE_MAP expanded to cover all 4 stages
  - Email backend configuration added for production
  - Message deduplication fix in orchestrator documented
  - is_verified re-check on cache hits added to retrieval description
  - API response schema corrected (stage_advanced, debate_mode added)
  - Session list endpoint messages exclusion documented
  - BudgetAlert PK normalized to UUID

TABLE OF CONTENTS
-----------------
  1.  Project Overview & Philosophy
  2.  High-Level Architecture Diagram
  3.  Full Project Folder Structure
  4.  Technology Stack & Dependencies
  5.  Environment Variables (.env) Reference
  6.  Virtual Environment (venv) Setup
  7.  Backend Architecture (Django Apps)
  8.  Database Schema (All Tables)
  9.  Redis Caching Architecture (4 Layers + Budget Flag)
  10. RAG (Retrieval-Augmented Generation) Layer
  11. Debate Engine Architecture
  12. AI / GPT Integration & Smart Model Routing
  13. Translation Architecture (Zero-Cost)
  14. Token Budget & Rate Limiting System
  15. Cost Monitoring & Budget Guard
  16. Frontend Architecture (React)
  17. UI/UX Design System & Styles
  18. API Endpoints Reference
  19. Infrastructure & Deployment Architecture
  20. Scaling Strategy
  21. Security Architecture
  22. Integration Map (All Systems)


================================================================================
SECTION 1 — PROJECT OVERVIEW & PHILOSOPHY
================================================================================

Project Name   : DoesGodExist.ai
Purpose        : An AI-powered intellectual debate engine that guides users
                 (atheists, agnostics, seekers, academics) through a structured
                 4-stage Islamic debate journey — from existence of God to
                 invitation to Islam — using RAG (Retrieval-Augmented Generation)
                 with verified scripture, scientific evidence, and Socratic logic.

Target Audience: Atheists, Agnostics, Seekers, Academics, Comparativists.

Core Differentiator:
  - Not a generic chatbot. A structured, stage-gated, evidence-driven debate
    engine with a clear intellectual journey.
  - Every scripture citation is pre-verified. AI never generates Quran/Hadith text.
  - Knowledge authority hierarchy ensures Quran always dominates.
  - Persona detection adapts tone automatically (keyword-based, zero cost).

Architecture v3 Philosophy (Lean, Cost-Aware, Survival Mode):
  - Monolith first — no microservices, no Kubernetes, single Django app on VPS
  - GPT-4o-mini as the default debate model (80% of turns)
  - GPT-4o reserved for complex philosophical turns only (20% of turns)
  - Open-source translation — Helsinki-NLP MarianMT via HuggingFace (free tier)
  - Pre-stored Quran/Hadith translations — ZERO translation API calls for scripture
  - Aggressive Redis caching at 4 layers — embedding, retrieval, response, translation
  - Budget cutoff flag stored in Redis (not process memory) — visible to all workers
  - pgvector on same Postgres instance — no separate vector database
  - Hard token budgets per user tier — anonymous, registered, premium
  - Hard monthly budget cap with auto-cutoff to protect the solo founder

Monthly Cost Estimate:
  - VPS (Hetzner CX21): $10–15/month
  - GPT-4o-mini (80% turns, ~2000 tokens/turn avg): $30–80/month
  - GPT-4o (20% turns, ~3500 tokens/turn avg): $25–60/month
  - Embeddings (text-embedding-3-small): $2–5/month
  - Translation (MarianMT via HuggingFace): $0
  - Redis, Celery, PostgreSQL (co-hosted): $0
  - Total: $70–160/month at 1K–5K users

  NOTE: Token estimates are based on: system prompt (~600 tokens) + RAG context
  (~1500 tokens average) + conversation history (~400 tokens) + user message
  (~150 tokens) + response (~600 tokens) = ~3250 tokens per gpt-4o-mini turn.
  The v2 estimate of 600 tokens/turn was incorrect.


================================================================================
SECTION 2 — HIGH-LEVEL ARCHITECTURE DIAGRAM
================================================================================

  [USER BROWSER]
       |
       | HTTPS
       v
  [NGINX] ──── static files ──── [React Frontend (SPA)]
       |
       | proxy_pass
       v
  [Gunicorn — 4 workers]
       |
       v
  [Django Application]
       |
       |── [DRF API Layer] ─────────────── auth / rate limit / throttle
       |
       v
  [DebateOrchestrator (services/)]
       |
       |── [StageGateValidator]           checks stage unlock conditions
       |── [PersonaDetector]              detects skeptic/seeker/academic from message
       |── [ComplexityRouter]             decides GPT-4o vs GPT-4o-mini
       |── [PromptBuilder]                constructs full prompt with context
       |── [RetrievalService]             fetches relevant knowledge chunks
       |── [GPTClient]                    calls OpenAI API
       |── [TranslationService]           translates output via HuggingFace
       |── [StageUpdater]                 updates debate stage on acceptance
       |── [TokenBudgetManager]           enforces per-user token limits
       v
  [PostgreSQL + pgvector]         stores all models + vector embeddings
       |
  [Redis]                         L1 embeddings / L2 retrieval / L3 response /
                                  L4 translation cache / L5 budget cutoff flag
       |
  [Celery Worker]                 async embedding jobs, daily reset tasks
       |
  [Celery Beat]                   hourly budget check, daily turn counter reset
       |
  [HuggingFace Inference API]     MarianMT translation (en→ar, en→ur, ar→en, ur→en)
       |
  [OpenAI API]                    GPT-4o-mini (default), GPT-4o (complex turns),
                                  text-embedding-3-small (embeddings)


================================================================================
SECTION 3 — FULL PROJECT FOLDER STRUCTURE
================================================================================

DoesGodExist_V2/backend
│
├── config/                         ← Django project configuration
│   ├── __init__.py                 ← imports celery_app for autodiscover
│   ├── settings.py                 ← all settings (env-driven)
│   ├── urls.py                     ← root URL routing
│   ├── wsgi.py                     ← WSGI entry point for Gunicorn
│   └── celery.py                   ← Celery app configuration
│
├── debate/                         ← Django app: core debate logic
│   ├── migrations/
│   ├── management/commands/        ← custom Django management commands
│   ├── models.py                   ← User, DebateSession, Message, PromptTemplate
│   ├── serializers.py              ← DRF serializers for API I/O
│   ├── views.py                    ← DebateMessageView (main API endpoint)
│   ├── urls.py                     ← app-level URL routing
│   ├── tasks.py                    ← Celery task: reset_daily_turns
│   ├── admin.py                    ← admin registration
│   └── apps.py
│
├── rag/                            ← Django app: Retrieval-Augmented Generation
│   ├── migrations/
│   ├── models.py                   ← Document, DocumentChunk (with VectorField)
│   ├── embedding_service.py        ← OpenAI embeddings + L1 cache
│   ├── retrieval_service.py        ← pgvector search + L2 cache + token budget
│   └── apps.py
│
├── indexing/                       ← Django app: data ingestion pipeline
│   ├── migrations/
│   ├── chunkers.py                 ← text chunking logic (Quran, Hadith, philosophy)
│   ├── pipeline.py                 ← IndexingPipeline class (bulk-safe)
│   ├── tasks.py                    ← Celery task: embed_chunks
│   ├── management/
│   │   └── commands/
│   │       ├── load_quran.py       ← management command to load Quran JSON
│   │       ├── load_hadith.py      ← management command to load Hadith JSON
│   │       └── load_philosophy.py  ← management command to load philosophy texts
│   └── apps.py
│
├── analytics/                      ← Django app: logging, budget, reporting
│   ├── migrations/
│   ├── models.py                   ← GPTLog, BudgetAlert
│   ├── tasks.py                    ← Celery task: hourly_budget_check
│   ├── budget_guard.py             ← BudgetGuard class (Redis-backed cutoff flag)
│   └── apps.py
│
├── services/                       ← Plain Python service layer (NOT a Django app)
│   ├── __init__.py
│   ├── orchestrator.py             ← DebateOrchestrator — main coordinator
│   ├── stage_validator.py          ← StageGateValidator — stage unlock logic
│   ├── stage_updater.py            ← StageUpdater — detects acceptance phrases
│   ├── persona_detector.py         ← PersonaDetector — keyword-based tone detection
│   ├── complexity_router.py        ← ComplexityRouter — GPT model selection
│   ├── prompt_builder.py           ← PromptBuilder — full prompt construction
│   ├── gpt_client.py               ← GPTClient — OpenAI API wrapper + L3 cache
│   └── translation_service.py     ← TranslationService — HuggingFace MarianMT
│
├── data/                           ← Source data files (not committed to git)
│   ├── quran.json                  ← Verified Quran verses (surah, ayah, arabic, english)
│   ├── hadith.json                 ← Sahih Hadith collection
│   ├── philosophy_texts/           ← Cosmological, ontological arguments (txt files)
│   │   ├── kalam_argument.txt
│   │   ├── fine_tuning_argument.txt
│   │   ├── moral_argument.txt
│   │   ├── ontological_argument.txt
│   │   ├── problem_of_evil_responses.txt
│   │   └── atheism_objections.txt
│   └── comparative_scripture/      ← Bible/Torah comparative passages (txt files)
│       ├── prophecies_of_muhammad.txt
│       └── comparative_theology.txt
│
├── frontend/                       ← React frontend (SPA)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatArea.jsx
│   │   │   │   ├── MessageBubble.jsx
│   │   │   │   └── MarkdownRenderer.jsx
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.jsx
│   │   │   │   └── Sidebar.jsx
│   │   │   └── ui/
│   │   │       ├── StageProgressBar.jsx
│   │   │       ├── LanguageSelector.jsx
│   │   │       ├── DebateModeSelector.jsx
│   │   │       └── ScriptureModal.jsx  ← Phase 2 feature (not in v1)
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx
│   │   │   ├── AuthPage.jsx            ← Phase 2 feature (not in v1)
│   │   │   └── SettingsPage.jsx        ← Phase 2 feature (not in v1)
│   │   ├── hooks/
│   │   │   ├── useDebate.js
│   │   │   └── useAuth.js              ← Phase 2 feature (not in v1)
│   │   ├── services/
│   │   │   └── api.js                  ← Axios API client
│   │   ├── store/
│   │   │   └── debateStore.js          ← Zustand state management
│   │   ├── styles/
│   │   │   ├── globals.css
│   │   │   └── markdown.css
│   │   ├── App.jsx                     ← Root with React Router v6
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── tests/
│   ├── test_stage_validator.py
│   ├── test_complexity_router.py
│   ├── test_stage_updater.py
│   ├── test_persona_detector.py
│   ├── test_orchestrator.py
│   └── test_api.py
│
├── logs/                           ← Runtime logs (not committed)
│   └── .gitkeep
├── venv/                           ← Python virtual environment (not committed)
├── manage.py
├── .env                            ← All secrets and config (never commit)
├── .gitignore
├── requirements.txt
└── README.md


================================================================================
SECTION 4 — TECHNOLOGY STACK & DEPENDENCIES
================================================================================

BACKEND
-------
Runtime         : Python 3.11+
Framework       : Django 4.2 LTS
API Layer       : Django REST Framework (DRF)
Authentication  : django-allauth + dj-rest-auth (Google OAuth, email/password)
                  NOTE: Apple OAuth is a future roadmap item — not implemented in v1.
Task Queue      : Celery 5.x
Task Scheduler  : Celery Beat (using built-in PersistentScheduler, NOT DatabaseScheduler)
                  IMPORTANT: Do NOT use django_celery_beat.schedulers:DatabaseScheduler
                  with settings.py CELERY_BEAT_SCHEDULE — the two are mutually exclusive.
                  This project uses the settings.py dict approach with PersistentScheduler.
Database        : PostgreSQL 15+ with pgvector extension
Cache/Broker    : Redis 7.x (also stores budget cutoff flag at key 'budget:cutoff_active')
AI              : OpenAI Python SDK (GPT-4o, GPT-4o-mini, text-embedding-3-small)
Translation     : HuggingFace Hub (Helsinki-NLP MarianMT models — en/ar/ur bidirectional)
Tokenizer       : tiktoken (OpenAI-compatible token counting)
Retry Logic     : tenacity
Environment     : python-dotenv
WSGI Server     : Gunicorn
Web Server      : Nginx

FULL PYTHON REQUIREMENTS (requirements.txt):

  django>=4.2,<5.0
  djangorestframework>=3.14
  psycopg2-binary>=2.9
  pgvector>=0.2.3
  django-allauth>=0.60
  dj-rest-auth>=5.0
  celery>=5.3
  redis>=5.0
  openai>=1.12
  tenacity>=8.2
  tiktoken>=0.6
  huggingface_hub>=0.20
  requests>=2.31
  python-dotenv>=1.0
  gunicorn>=21.2
  whitenoise>=6.6           (serve static files from Django)
  django-cors-headers>=4.3  (allow React frontend to call API)

FRONTEND
--------
Runtime         : Node.js 20 LTS
Framework       : React 18 + Vite
Routing         : React Router v6 (wired in App.jsx — single route / to ChatPage)
State           : Zustand
API Client      : Axios
Markdown        : react-markdown + remark-gfm + rehype-sanitize
Styling         : Tailwind CSS
Icons           : Lucide React
Authentication  : @react-oauth/google (Google Sign-In button)
Build Tool      : Vite 5.x

FRONTEND PACKAGE.JSON KEY DEPENDENCIES:
  "react": "^18.2.0"
  "react-dom": "^18.2.0"
  "react-router-dom": "^6.21"
  "axios": "^1.6"
  "zustand": "^4.5"
  "react-markdown": "^9.0"
  "remark-gfm": "^4.0"
  "rehype-sanitize": "^6.0"
  "tailwindcss": "^3.4"
  "lucide-react": "^0.300"
  "@react-oauth/google": "^0.12"


================================================================================
SECTION 5 — ENVIRONMENT VARIABLES (.env) REFERENCE
================================================================================

Create this file at project root (same level as manage.py).
NEVER commit this file. Add .env to .gitignore.

NOTE: DATABASE_URL is NOT used. settings.py reads individual DB_* variables.
      Do not define DATABASE_URL — it will be silently ignored and cause confusion.

# ── DJANGO CORE ──────────────────────────────────────────────────────────────
DEBUG=True
SECRET_KEY=your-random-50-char-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://doesgodexist.ai

# ── DATABASE (individual vars — NOT DATABASE_URL) ────────────────────────────
DB_NAME=doesgodexist
DB_USER=postgres
DB_PASSWORD=your_strong_password
DB_HOST=localhost
DB_PORT=5432

# ── REDIS ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── OPENAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-your-openai-key-here
EMBEDDING_MODEL=text-embedding-3-small
GPT_MINI_MODEL=gpt-4o-mini
GPT_STRONG_MODEL=gpt-4o

# ── HUGGING FACE ──────────────────────────────────────────────────────────────
HF_API_URL=https://api-inference.huggingface.co/models
HF_API_TOKEN=                          # Optional — increases free rate limit

# ── BUDGET & ALERTS ───────────────────────────────────────────────────────────
MONTHLY_BUDGET_USD=300
FOUNDER_EMAIL=you@example.com

# ── EMAIL (required for budget alerts in production) ──────────────────────────
EMAIL_HOST=smtp.mailgun.org            # or smtp.sendgrid.net, etc.
EMAIL_PORT=587
EMAIL_HOST_USER=postmaster@doesgodexist.ai
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@doesgodexist.ai

# ── AUTH (Google OAuth) ────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

# ── LOCAL DEV ONLY (LLaMA 2 backend — remove before production) ──────────────
# LLM_BACKEND=llama
# LLAMA_MODEL=llama2
# OLLAMA_URL=http://localhost:11434
# EMBEDDING_BACKEND=local

# ── PRODUCTION OVERRIDES ──────────────────────────────────────────────────────
# DEBUG=False
# ALLOWED_HOSTS=doesgodexist.ai,www.doesgodexist.ai
# DB_HOST=localhost  (Postgres stays local on VPS)
# SENTRY_DSN=https://...ingest.sentry.io/...


================================================================================
SECTION 6 — VIRTUAL ENVIRONMENT (venv) SETUP
================================================================================

CREATING THE VIRTUAL ENVIRONMENT:

  $ cd doesgodexist/                 # navigate to project root
  $ python3 -m venv venv             # create virtual environment
  $ source venv/bin/activate         # Linux/Mac: activate
  $ venv\Scripts\activate            # Windows: activate

INSTALLING ALL DEPENDENCIES:

  $ pip install --upgrade pip
  $ pip install -r requirements.txt

COMMON venv OPERATIONS:

  $ deactivate                       # deactivate when done
  $ source venv/bin/activate         # re-activate
  $ pip freeze > requirements.txt    # save current packages

IMPORTANT RULES:
  - Always activate venv before running manage.py commands
  - Always activate venv before starting Celery workers
  - The venv/ directory should be in .gitignore
  - Never pip install inside the project without activating venv first
  - When deploying to VPS: recreate venv on server, never copy it


================================================================================
SECTION 7 — BACKEND ARCHITECTURE (DJANGO APPS)
================================================================================

The backend is a Django monolith split into 4 apps + 1 services layer.

─────────────────────────────────────────────────────
APP 1: debate/
─────────────────────────────────────────────────────
Purpose: Core debate logic, user management, session management.

Contains:
  - User model (custom AbstractBaseUser)
  - DebateSession model
  - Message model
  - PromptTemplate model
  - DRF views (DebateMessageView — main API endpoint)
  - DRF serializers
  - debate/tasks.py (daily turn reset Celery task)

Key Design Decisions:
  - Custom User model uses is_anonymous_user (NOT is_anonymous — that's a Django
    built-in property that checks is_authenticated, not our field)
  - DebateSession tracks stage progression and acceptance flags
  - Message stores every turn including retrieved chunk IDs and citations
  - PromptTemplate allows live editing of debate prompts without code deploy
  - Session ownership is enforced in ALL views that accept session_id

─────────────────────────────────────────────────────
APP 2: rag/
─────────────────────────────────────────────────────
Purpose: All knowledge management — documents, chunks, embeddings, retrieval.

Contains:
  - Document model (title, source type, indexing status)
  - DocumentChunk model (content, arabic/urdu versions, 1536-dim vector, stage tags)
  - EmbeddingService (OpenAI text-embedding-3-small + L1 Redis cache)
  - RetrievalService (pgvector cosine search + L2 cache + token budget)

Key Design Decisions:
  - pgvector is co-hosted on the same Postgres instance (no Pinecone cost)
  - text-embedding-3-small uses 1536 dimensions (not 3072 — saves RAM and cost)
  - stage_tags ArrayField filters retrieval to current debate stage (no cross-stage noise)
  - top_k=8 chunks is the default
  - is_verified=True required for Quran/Hadith chunks — ensures only vetted data retrieval
  - On cache hit, is_verified=True filter is re-applied to prevent stale unverified chunks

─────────────────────────────────────────────────────
APP 3: indexing/
─────────────────────────────────────────────────────
Purpose: Data ingestion pipeline — loads Quran, Hadith, philosophy, comparative
         scripture into DB.

Contains:
  - chunkers.py (smart chunking: one Quran ayah = one chunk; never split)
  - pipeline.py (IndexingPipeline — idempotent, uses bulk_create for performance)
  - tasks.py (Celery async task: embed_chunks)
  - management commands: load_quran, load_hadith, load_philosophy
    (load_philosophy also loads comparative_scripture/)

Key Design Decisions:
  - Quran ayahs are NEVER split across chunks — each ayah is exactly one chunk
  - Hadith chunks store grade (sahih/hasan) — only is_verified=True are retrieved by default
  - Philosophy texts chunked at max 450 tokens with 64-token overlap for continuity
  - content_urdu is populated for Quran verses from a verified Urdu translation JSON
  - Ingestion is idempotent — safe to re-run without creating duplicate chunks
  - Uses bulk_create with update_conflicts=True for efficient large-scale ingestion
  - SURAH_STAGE_MAP covers all 114 surahs across all 4 debate stages
  - Celery handles embedding asynchronously — ingestion and embedding are decoupled

SURAH → STAGE COVERAGE POLICY:
  Every surah must be mapped to at least one stage. The mapping file
  (load_quran.py) groups surahs by primary thematic relevance. Surahs that are
  relevant to multiple stages (e.g. Al-Imran covers existence + prophethood)
  can appear in multiple stage_tags. No surah defaults to ['general'] — that
  tag has no effect in retrieval because no query uses stage='general'.

─────────────────────────────────────────────────────
APP 4: analytics/
─────────────────────────────────────────────────────
Purpose: Full cost tracking, GPT logging, budget protection.

Contains:
  - GPTLog model (every GPT call logged: model, tokens, cost, latency, cache layer)
  - BudgetAlert model (50%, 80%, 100% threshold alerts)
  - BudgetGuard class (hourly budget check + email alerts + Redis cutoff flag)
  - Celery beat task: hourly_budget_check

Key Design Decisions:
  - Every single GPT API call is logged — never fly blind on costs
  - Budget cutoff stored as Redis key 'budget:cutoff_active' (TTL: end of month)
    This ensures ALL Gunicorn workers and Celery workers see the same flag,
    solving the process-memory split-brain problem from v2.
  - Monthly alerts at 50%, 80%, 100% with email to founder
  - Email uses SMTP settings from .env (not hardcoded console backend)
  - Admin dashboard metrics: cost/session, cache hit rates, model routing distribution

─────────────────────────────────────────────────────
SERVICES LAYER: services/
─────────────────────────────────────────────────────
Purpose: Business logic layer — NOT a Django app. Plain Python service classes.
         Imported by views but also callable from management commands and tests.

Contains:
  - orchestrator.py        — DebateOrchestrator (coordinates all services)
  - stage_validator.py     — StageGateValidator (enforces stage progression)
  - stage_updater.py       — StageUpdater (detects acceptance phrases → advance stage)
  - persona_detector.py    — PersonaDetector (keyword-based skeptic/seeker/academic)
  - complexity_router.py   — ComplexityRouter (routes to GPT-4o vs GPT-4o-mini)
  - prompt_builder.py      — PromptBuilder (assembles full structured prompt)
  - gpt_client.py          — GPTClient (OpenAI API wrapper + L3 response cache)
  - translation_service.py — TranslationService (HuggingFace MarianMT + L4 cache)

Key Design Decisions:
  - Services layer is separated from Django apps intentionally.
  - This allows unit testing without Django context.
  - Orchestrator wires everything together in a clean pipeline.
  - PersonaDetector is called once at session start and on every turn if not yet set.
    Once detected, the persona is saved to DebateSession.detected_persona and reused.


================================================================================
SECTION 8 — DATABASE SCHEMA (ALL TABLES)
================================================================================

DATABASE: PostgreSQL 15+ | EXTENSION: pgvector

─────────────────────────────────────────────────────
TABLE: debate_user  (custom AUTH_USER_MODEL)
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  email             VARCHAR(254)  UNIQUE, nullable (anonymous users have no email)
  session_key       VARCHAR(64)   INDEX, nullable (for anonymous user tracking)
  is_anonymous_user BOOLEAN       default=False
                                  NOTE: field is named is_anonymous_user, NOT is_anonymous.
                                  Django's AbstractBaseUser has a built-in property
                                  called is_anonymous that checks is_authenticated.
                                  Using the same name would shadow it silently.
  tier              VARCHAR(20)   choices: anonymous / registered / premium
  preferred_language VARCHAR(5)   choices: en / ar / ur, default=en
  daily_turn_count  INTEGER       default=0 (reset daily via Celery beat)
  daily_reset_date  DATE          nullable
  is_staff          BOOLEAN       default=False
  is_active         BOOLEAN       default=True
  created_at        TIMESTAMP     auto_now_add
  deleted_at        TIMESTAMP     nullable (soft delete)
  metadata          JSONB         default={}
  password          VARCHAR(128)  (from AbstractBaseUser)

INDEXES:
  - email UNIQUE
  - session_key (non-unique, for anonymous lookup)

─────────────────────────────────────────────────────
TABLE: debate_debatesession
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  user_id           UUID          FK → debate_user, ON DELETE PROTECT
  current_stage     VARCHAR(30)   choices: existence / prophethood / muhammad / invitation
  debate_mode       VARCHAR(30)   choices: standard / scientific / philosophical /
                                           reflective / comparative / prophethood_mode
  detected_persona  VARCHAR(20)   choices: skeptic / seeker / academic; nullable
                                  Set by PersonaDetector on first detection, persisted.
                                  Never left permanently None after first user message.
  god_acceptance    BOOLEAN       nullable (True = accepted, False = not yet, None = not assessed)
  prophecy_acceptance BOOLEAN     nullable
  muhammad_acceptance BOOLEAN     nullable
  complexity_score  FLOAT         default=0.0 (rolling average of turn complexity)
  total_tokens      INTEGER       default=0
  total_cost_usd    DECIMAL(8,6)  default=0
  created_at        TIMESTAMP     auto_now_add
  updated_at        TIMESTAMP     auto_now (tracks last activity)
  completed_at      TIMESTAMP     nullable
  deleted_at        TIMESTAMP     nullable (soft delete)
  metadata          JSONB         default={}

INDEXES:
  - (user_id, current_stage, created_at) composite

STAGE GATE LOGIC:
  prophethood stage requires: god_acceptance = True
  muhammad stage requires:    god_acceptance = True AND prophecy_acceptance = True
  invitation stage requires:  god_acceptance = True AND prophecy_acceptance = True
                              AND muhammad_acceptance = True

STAGE REGRESSION POLICY:
  Acceptance flags are ONE-WAY only. Once god_acceptance=True, it cannot be set
  back to False even if the user says "I changed my mind." The session stays at the
  advanced stage. The AI (via prompt instructions) handles verbal reversals gracefully
  without the backend needing to regress. This is intentional — the debate continues
  forward, re-addressing concerns at the current stage.

  NEGATION GUARD: The StageUpdater checks for negation patterns BEFORE setting flags.
  Phrases like "I don't accept", "I no longer believe", "I changed my mind" suppress
  acceptance detection even if acceptance keywords are also present.

─────────────────────────────────────────────────────
TABLE: debate_message
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  session_id        UUID          FK → debate_debatesession, ON DELETE CASCADE
  role              VARCHAR(10)   choices: user / assistant
  content           TEXT          full message content
  stage             VARCHAR(30)   current debate stage when message was created
  token_count       INTEGER       default=0
  retrieved_chunk_ids JSONB       list of DocumentChunk UUIDs used
  citations         JSONB         list of citation objects {ref, source, type}
  is_fallacy_detected BOOLEAN     default=False
  fallacy_types     JSONB         list of fallacy names detected
  sequence_num      INTEGER       ordering within session
  created_at        TIMESTAMP     auto_now_add

INDEXES:
  - (session_id, sequence_num)
  - (session_id, stage)

NOTE: sequence_num is per-session (user + assistant messages combined).
      A session's first user message is seq=0, first assistant message is seq=1, etc.

─────────────────────────────────────────────────────
TABLE: debate_prompttemplate
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  stage             VARCHAR(30)   which debate stage this template applies to
  version           INTEGER       template version number
  is_active         BOOLEAN       default=True (only one active per stage)
  system_template   TEXT          system prompt template for GPT
  context_template  TEXT          context injection template
  tone              VARCHAR(30)   choices: logical / scientific / reflective / philosophical
  created_at        TIMESTAMP     auto_now_add

UNIQUE CONSTRAINT: (stage, version)

─────────────────────────────────────────────────────
TABLE: rag_document
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  title             VARCHAR(512)
  source_type       VARCHAR(20)   choices: quran / hadith / philosophy / argument /
                                           scripture_comparative
  author            VARCHAR(256)  nullable
  checksum          VARCHAR(64)   UNIQUE (SHA256 of title — prevents duplicate ingestion)
  indexing_status   VARCHAR(20)   choices: pending / processing / complete / failed
  chunk_count       INTEGER       default=0
  created_at        TIMESTAMP     auto_now_add
  deleted_at        TIMESTAMP     nullable
  metadata          JSONB         default={}

─────────────────────────────────────────────────────
TABLE: rag_documentchunk
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  document_id       UUID          FK → rag_document, ON DELETE PROTECT
  chunk_index       INTEGER       position within parent document
  content           TEXT          English text content
  content_arabic    TEXT          Arabic content (Quran/Hadith only), nullable
  content_urdu      TEXT          Urdu translation (Quran only, from verified JSON), nullable
  embedding         VECTOR(1536)  pgvector — text-embedding-3-small dimensions; nullable
  token_count       INTEGER       pre-computed token count
  chunk_type        VARCHAR(30)   quran / hadith / philosophy / argument / comparative
  stage_tags        TEXT[]        e.g. ['existence'], ['prophethood', 'muhammad']
  topic_tags        TEXT[]        e.g. ['tawhid', 'cosmological', 'embryology']
  source_ref        JSONB         {surah, ayah} or {collection, number, grade}
  embedding_model   VARCHAR(64)   default='text-embedding-3-small'
  embedding_version INTEGER       default=1 (allows re-embedding with new models)
  is_verified       BOOLEAN       default=False (True for Quran + Sahih/Hasan Hadith only)
  created_at        TIMESTAMP     auto_now_add
  deleted_at        TIMESTAMP     nullable

INDEXES:
  - (chunk_type, embedding_version)
  - (is_verified, deleted_at)
  - GIN index on stage_tags  (for ArrayField contains queries — CRITICAL for performance)
  - GIN index on topic_tags
  - pgvector HNSW index on embedding (created separately for ANN search)

PGVECTOR INDEX (run after migrate, after data is loaded):
  CREATE INDEX idx_chunk_embedding ON rag_documentchunk
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

NOTE ON content_urdu:
  Quran chunks must have content_urdu populated from a verified Urdu Quran JSON
  (e.g. Fateh Muhammad Jalandhry translation, available on tanzil.net).
  The load_quran management command accepts an optional --urdu-file argument.
  This field is NOT auto-translated — it must be pre-stored from a verified source.

─────────────────────────────────────────────────────
TABLE: analytics_gptlog
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4
  session_id        UUID          FK → debate_debatesession, ON DELETE PROTECT
  message_id        UUID          FK → debate_message, ON DELETE SET NULL; nullable
  model_used        VARCHAR(64)   which GPT model was actually called
  routing_reason    VARCHAR(100)  why that model was chosen
  prompt_tokens     INTEGER
  completion_tokens INTEGER
  total_tokens      INTEGER
  cost_usd          DECIMAL(8,6)  computed cost in USD
  latency_ms        INTEGER       end-to-end API latency in milliseconds
  prompt_hash       VARCHAR(64)   SHA256 of prompt (for cache deduplication)
  cache_layer       VARCHAR(10)   nullable: L1 / L2 / L3 / None
  cache_hit         BOOLEAN       default=False
  error             JSONB         nullable (error details if call failed)
  created_at        TIMESTAMP     auto_now_add

─────────────────────────────────────────────────────
TABLE: analytics_budgetalert
─────────────────────────────────────────────────────
  id                UUID          PK, default=uuid4  (normalized from AUTO INT in v2)
  month             DATE          first day of the month (e.g., 2025-03-01)
  total_cost_usd    DECIMAL(8,4)  total GPT cost so far this month
  alert_level       VARCHAR(10)   choices: 50pct / 80pct / 100pct
  is_cutoff_active  BOOLEAN       default=False (True at 100% = no new GPT calls)
  created_at        TIMESTAMP     auto_now_add


================================================================================
SECTION 9 — REDIS CACHING ARCHITECTURE (5 LAYERS)
================================================================================

Redis is co-hosted on the same VPS. Used for 5 distinct purposes:
  4 caching layers + 1 global budget cutoff flag + Celery broker.

LAYER   | WHAT IS CACHED             | KEY PATTERN                        | TTL     | EST. HIT RATE
--------|----------------------------|------------------------------------|---------|---------------
L1      | Query embeddings           | emb:{model}:{sha256(text)}         | 30 days | 70–80%
L2      | Retrieval results          | ret:{stage}:{sha256(query)}        | 24 hrs  | 50–60%
L3      | Full GPT responses         | resp:{sha256(prompt_dict)}         | 6 hrs   | 20–30%
L4      | Translated responses       | trans:{lang}:{md5(text)}           | 7 days  | 60–70%
L4b     | English translation of     | trans_in:{lang}:{md5(text)}        | 24 hrs  | 40–50%
        | user input (before RAG)    |                                    |         |
Budget  | Monthly cutoff flag        | budget:cutoff_active               | TTL to  | N/A (flag)
Flag    |                            |                                    | month end|

COMBINED EFFECT:
  At steady state, 60–70% of embedding calls and 20–30% of GPT calls are served
  from cache. This reduces monthly GPT cost by approximately 35%.

IMPORTANT RULES:
  - L3 (response cache) is only active when temperature < 0.3
  - Never cache Quran Arabic text through L4 — it is pre-stored, not translated
  - L1 cache persists 30 days because user argument patterns repeat significantly
  - L2 cache is 24 hours to allow knowledge base updates to take effect daily
  - L4b (inbound translation cache) uses a separate key prefix from L4 outbound
  - On L2 cache hit, the retrieved chunks are re-fetched with is_verified=True filter
    re-applied to prevent stale unverified data from being used

BUDGET CUTOFF FLAG:
  Key: 'budget:cutoff_active'
  Value: '1' (string) when active
  TTL: seconds until end of current month (auto-expires at month rollover)
  Written by: BudgetGuard.check() inside the Celery worker
  Read by: DebateOrchestrator.run() in every Gunicorn worker
  This shared Redis flag ensures all processes see the cutoff simultaneously.

REDIS CONFIGURATION IN SETTINGS:
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.redis.RedisCache',
          'LOCATION': os.getenv('REDIS_URL'),
      }
  }
  CELERY_BROKER_URL = os.getenv('REDIS_URL')
  CELERY_RESULT_BACKEND = os.getenv('REDIS_URL')


================================================================================
SECTION 10 — RAG (RETRIEVAL-AUGMENTED GENERATION) LAYER
================================================================================

RAG is the knowledge backbone of the debate engine. Every GPT response must be
grounded in verified knowledge from the database — never hallucinated.

KNOWLEDGE BASE COMPOSITION (10 source files, 7 chunk types):

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ File                                          │ Chunk Type  │ Stages        │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │ Quran/quran_debate_ready_FINAL.json           │ quran       │ 1, 2, 3, 4   │
  │ hadith/sahih_bukhari_final.json               │ hadith      │ 2, 3, 4      │
  │ philosophy/stage1_existence_of_god.json       │ philosophy  │ 1            │
  │ philosophy/stage2_necessity_of_prophethood.json│ philosophy  │ 2            │
  │ philosophy/stage3_prophethood_of_muhammad.json │ philosophy  │ 3            │
  │ science_and_religion/scientific_signs_v2.json │ scientific  │ 1, 3         │
  │ comparative_religion/Islam_comparison*.json   │ comparative │ 1, 4         │
  │ logic/reasoning_framework.json                │ logic       │ 1, 2, 3, 4   │
  │ meta/debate_topics.json                       │ meta        │ 1, 2, 3, 4   │
  │ meta/glossary.json                            │ meta        │ 1, 2, 3, 4   │
  └─────────────────────────────────────────────────────────────────────────────┘

  DOCUMENT SOURCE TYPES (Document.source_type field):
    'quran'                — Quran verses (quran_debate_ready_FINAL.json)
    'hadith'               — Hadith collections (sahih_bukhari_final.json)
    'philosophy'           — Rational arguments, stage-specific JSON files
    'scientific'           — Scientific signs in Quran/Hadith
    'comparative_religion' — Interfaith comparison topics (Islam/Christianity/Judaism)
    'logic'                — Reasoning framework, fallacy detection toolkit
    'meta'                 — Debate topics map, glossary of terms

  DOCUMENTCHUNK CHUNK TYPES (DocumentChunk.chunk_type field):
    'quran'       — One ayah per chunk. is_verified=True always.
    'hadith'      — One hadith per chunk. is_verified=True for Sahih/Hasan.
    'philosophy'  — One argument per chunk (premises + responses). is_verified=False.
    'scientific'  — One scientific sign entry per chunk. is_verified=False.
    'comparative' — One interfaith topic per chunk. is_verified=False.
    'logic'       — One fallacy/strategy entry per chunk. is_verified=False.
    'meta'        — One debate topic or glossary term per chunk. is_verified=False.

  NOTE on is_verified:
    True  → Used in retrieval by default. Scripture only (Quran + Sahih/Hasan hadith).
    False → Retrieved but presented with appropriate epistemic framing.
             The AI prompt instructs it to mark philosophical/scientific content
             as "argument" or "alignment" not as "established fact".

  STAGE TAGS — VALID VALUES (used in stage_tags ArrayField):
    'existence'    — Stage 1: Existence of God
    'prophethood'  — Stage 2: Necessity of Prophethood
    'muhammad'     — Stage 3: Prophethood of Muhammad SAW
    'invitation'   — Stage 4: Invitation to Islam

    NOTE: The raw JSON datasets use verbose strings ("existence_of_god") and
    integers (1, 2, 3, 4). The indexing pipeline normalises ALL of these to
    the short internal strings above before writing to the database.
    The retrieval service always queries using the short form.
    Never store verbose strings or integers in stage_tags — normalise on ingest.

  RETRIEVAL PRIORITY ORDER (how the prompt builder orders retrieved chunks):
    1. quran       — highest authority, always cited first in context block
    2. hadith      — secondary scripture, cited after Quran
    3. scientific  — supporting evidence for Stage 1/3 scientific arguments
    4. philosophy  — rational arguments, Kalam, fine-tuning etc.
    5. comparative — interfaith comparison (Stage 3/4 only)
    6. logic       — fallacy detection, burden of proof (any stage)
    7. meta        — socratic questions, debate topic guidance (any stage)

  MANAGEMENT COMMANDS (one per source file):
    $ python manage.py load_quran
    $ python manage.py load_hadith
    $ python manage.py load_philosophy
    $ python manage.py load_scientific_signs
    $ python manage.py load_comparative_religion
    $ python manage.py load_logic
    $ python manage.py load_meta

  EXPECTED CHUNK COUNTS AFTER FULL LOAD:
    quran       : ~6,200+ (one chunk per ayah)
    hadith      : ~7,563  (one chunk per hadith, per Bukhari metadata)
    philosophy  : ~15–20  (5–7 arguments per stage file)
    scientific  : ~41     (per file metadata)
    comparative : ~8      (one per comparison topic)
    logic       : ~10–20  (fallacies + strategies)
    meta        : ~20–30  (debate topics + glossary terms)
    ─────────────────────────────────────────
    TOTAL       : ~13,900+ chunks

  EMBEDDING NOTE:
    All chunks use OpenAI text-embedding-3-small (1536 dimensions).
    The embedding content is the 'content' field (English text only).
    Arabic and Urdu are stored separately and injected into the prompt
    after retrieval — they are NOT embedded or used for vector search.


RETRIEVAL FLOW:
  1. User message arrives (already translated to English if non-English)
  2. EmbeddingService converts message to 1536-dim vector (checks L1 cache first)
  3. RetrievalService queries pgvector using cosine distance
  4. Filtered by: stage_tags contains current_stage AND is_verified=True
                  AND deleted_at IS NULL AND embedding IS NOT NULL
  5. Top 8 chunks returned
  6. Token budget enforced: maximum 2500 tokens of context injected
  7. Results cached in L2 for 24 hours (identical queries reuse results)
  8. On L2 cache hit: chunk IDs fetched from cache but is_verified=True filter
     re-applied in the DB query to prevent stale data

CONTEXT COMPRESSION:
  If chunks exceed token budget:
  - Philosophy/argument chunks > 200 tokens: compressed to 150 tokens via GPT-4o-mini
  - Quran/Hadith chunks: NEVER compressed — they are already minimal
  - Compressed versions cached permanently (never re-compressed)

DATA REQUIREMENTS & LOAD INSTRUCTIONS:

  QURAN:
    Download verified Quran JSON from: github.com/risan/quran-json or tanzil.net
    Format: [{surah: 2, ayah: 255, arabic: "اللّهُ لاَ إِلَـهَ...", english: "Allah..."}]
    Place at: data/quran.json

    Optionally, for Urdu pre-storage:
    Format: same structure with additional "urdu" field per verse
    Place at: data/quran_urdu.json
    Run: python manage.py load_quran --urdu-file data/quran_urdu.json

  HADITH:
    Use Sahih Bukhari and Sahih Muslim datasets (public domain)
    Store with grade field: sahih / hasan / daif
    Only sahih and hasan are marked is_verified=True and retrieved by default

  PHILOSOPHY:
    Plain text files in data/philosophy_texts/ (see Section 3 for file list)
    Run: python manage.py load_philosophy
    These chunks are is_verified=False but included in retrieval for philosophy/
    scientific debate modes where Quran context alone is insufficient.

  COMPARATIVE SCRIPTURE:
    Plain text files in data/comparative_scripture/
    Loaded as source_type='comparative_religion', chunk_type='comparative'
    stage_tags: ['muhammad', 'invitation'] (used in Stages 3–4 comparative mode)
    is_verified=False (never cite as absolute truth — for comparative analysis only)

================================================================================
SECTION 11 — DEBATE ENGINE ARCHITECTURE
================================================================================

The debate engine is the product. RAG is just a subsystem.

STAGE SYSTEM (4 Stages):
  Stage 1 — Existence of God      (starting stage, always unlocked)
  Stage 2 — Prophethood/Prophecy  (unlocked when god_acceptance=True)
  Stage 3 — Muhammad (SAW)        (unlocked when prophecy_acceptance=True)
  Stage 4 — Invitation to Islam   (unlocked when muhammad_acceptance=True)

DEBATE MODES (6 Modes):
  1. Standard Mode           — Quranic verses, scientific miracles, Stage 1
  2. Deep Philosophy Mode    — Logic, reasoning, classical arguments, Stage 1
  3. Scientific Mode         — Empirical/cosmological arguments, Stage 1
  4. Comparative Religions   — Islam vs Christianity vs Judaism, Stage 3–4
  5. Prophethood Mode        — Evidence for Muhammad (SAW), Stage 3
  6. Reflective Mode         — Gentle, exploratory, Stage 1–2

PERSONA DETECTION (services/persona_detector.py):
  Runs on every user message. Once detected and saved, skips re-detection.
  Detection is keyword-based (zero LLM cost).

  SKEPTIC/ATHEIST indicators:
    - "don't believe", "prove it", "no evidence", "religion is", "science says",
      "evolution", "big bang", "random", "naturalistic", "burden of proof"
    → Tone: logical. Evidence-first, epistemological questions.

  SEEKER/AGNOSTIC indicators:
    - "not sure", "curious", "seeking", "wondering", "open to", "maybe",
      "what if", "searching", "looking for meaning", "I want to understand"
    → Tone: reflective. Exploratory, warm, existential questions.

  ACADEMIC indicators:
    - "argue", "premise", "conclusion", "logical", "fallacy", "philosophy",
      "epistemology", "ontology", "teleological", "kalam", "syllogism", "peer-reviewed"
    → Tone: philosophical. Formal, Socratic, citation-heavy.

  DEFAULT (no clear signal): skeptic/logical.

STAGE GATE VALIDATOR (services/stage_validator.py):
  Rules:
    prophethood gate: god_acceptance must be True
    muhammad gate:    god_acceptance AND prophecy_acceptance must be True
    invitation gate:  all three acceptances must be True

STAGE UPDATER (services/stage_updater.py):
  Detects acceptance phrases in user messages (keyword matching — no LLM cost).

  NEGATION GUARD (applied first, suppresses acceptance if found):
    "don't", "do not", "doesn't", "not", "no longer", "changed my mind",
    "take that back", "actually", "never mind", "disagree"

  God acceptance triggers (only if no negation found):
    "i accept", "you convinced me", "god exists", "i believe",
    "makes sense", "i agree", "that is convincing", "fair point", "i concede"

  Prophecy acceptance triggers:
    "prophets make sense", "prophecy is reasonable", "i accept prophets",
    "guidance makes sense", "need for guidance"

  Muhammad acceptance triggers:
    "muhammad was a prophet", "i accept muhammad", "quran is divine",
    "quran could not be written by a human", "quran is from god"

  When detected: sets acceptance flag, attempts to advance to next stage.
  Flags are ONE-WAY — once True, cannot be reverted programmatically.

COMPLEXITY ROUTER (services/complexity_router.py):
  Signals for COMPLEX → GPT-4o (score >= 2 triggers upgrade):
  - Keywords: prove, disprove, contradiction, paradox, evolution, quantum,
              multiverse, peer-reviewed, scientific consensus, darwin, big bang
  - Message length > 350 characters
  - Session TURN count > 8 (turn = user messages only, not total messages)
  Result: ~80% of turns use GPT-4o-mini
          ~20% of turns use GPT-4o

  TURN COUNT FIX: session.messages.filter(role='user').count() is used for the
  turn depth check — not session.messages.count() which would include assistant
  messages and trigger GPT-4o too early.

PROMPT BUILDER (services/prompt_builder.py):
  Assembles the full prompt package:
  1. System message: stage + persona + tone + formatting rules
  2. Context block: retrieved chunks with source references
  3. History: last 6 PRIOR messages (NOT including the current user message)
  4. Current user message

  CRITICAL: The current user message is NOT included in history.
  The orchestrator saves the user message to DB first, then calls
  PromptBuilder. History is fetched as the last 8 messages excluding the
  most recently saved one. This prevents the user message appearing twice.

  Persona → Tone mapping:
    skeptic   → logical
    seeker    → reflective
    academic  → philosophical
    None      → logical (default)


================================================================================
SECTION 12 — AI / GPT INTEGRATION & SMART MODEL ROUTING
================================================================================

MODELS USED:
  text-embedding-3-small  — document and query embeddings (1536 dimensions)
  gpt-4o-mini             — default debate responses (80% of turns)
  gpt-4o                  — complex philosophical turns (20% of turns)

COST PER TOKEN (as of architecture v3):
  gpt-4o-mini: input=$0.00000015, output=$0.0000006
  gpt-4o:      input=$0.000005,   output=$0.000015

REALISTIC COST PER DEBATE TURN:
  A typical turn consists of:
    System prompt:        ~600  tokens  (from PromptTemplate or default)
    RAG context (8 chunks): ~1500 tokens (varies by chunk type)
    History (6 msgs):     ~400  tokens
    User message:         ~150  tokens
    TOTAL INPUT:          ~2650 tokens
    Response (output):    ~600  tokens
    TOTAL:                ~3250 tokens

  gpt-4o-mini turn: ~$0.00082  (2650 input + 600 output tokens)
  gpt-4o turn:      ~$0.022    (2650 input + 600 output tokens)
  Embedding query:  ~$0.000001 (cached ~80% of the time)
  Translation:      $0.00      (MarianMT, free)
  Average per turn (80/20 split): ~$0.00656 + ~$0.004 = ~$0.005–0.010/turn

  NOTE: v2 estimated $0.00036/turn for gpt-4o-mini. This was based on 600 total
  tokens, which assumed no system prompt or context. The correct estimate with a
  full system prompt and RAG context is 5–8x higher. Monthly budget should be
  planned accordingly.

MODEL ROUTING TABLE:
  Task                          | Model           | Reason
  ------------------------------|-----------------|----------------------------------
  Main debate response          | gpt-4o-mini     | Best cost/quality for structured
  Complex philosophical turns   | gpt-4o          | Multi-step deep reasoning
  Stage signal detection        | Rule-based      | Keyword matching, $0
  Persona detection             | Rule-based      | Keyword matching, $0
  Context compression           | gpt-4o-mini     | Summarize long philosophy chunks
  Translation                   | MarianMT        | Free, sufficient quality for UI

GPT CLIENT (services/gpt_client.py):
  - Wraps OpenAI client
  - Checks L3 response cache before API call
  - Sets temperature=0.3 (low for consistency, cacheable)
  - Computes cost from token counts
  - Handles unknown model names gracefully (logs warning, uses gpt-4o-mini rates)
  - Records latency
  - Returns GPTResponse dataclass

DEV/TESTING — LLaMA 2 FALLBACK (OPTIONAL):
  For local development: set LLM_BACKEND=llama in .env
  Uses Ollama (localhost:11434) and all-MiniLM-L6-v2 for embeddings (384-dim local)
  WARNING: Local embeddings are 384-dim vs 1536-dim production. Do NOT mix.
  Always re-embed all chunks when switching between backends.


================================================================================
SECTION 13 — TRANSLATION ARCHITECTURE (ZERO-COST)
================================================================================

Translation Strategy — 3 Layers, Zero API Cost:

  Layer 1 — Pre-Stored (DB):
    Quran verses stored with verified Arabic + Urdu + English already in DB.
    ZERO translation calls for scripture. Never use AI to translate Quran Arabic.

  Layer 2 — Cached (Redis L4 / L4b):
    L4:  If same GPT response was previously translated, serve from Redis (7 days).
    L4b: If same user input was previously translated to English, serve from Redis
         (24 hours). Prevents re-translation of common questions.

  Layer 3 — Live Translation:
    Only for new, uncached GPT-generated responses or new user inputs.
    Uses Helsinki-NLP MarianMT via HuggingFace free Inference API.

MODELS USED:
  en → ar (response):  Helsinki-NLP/opus-mt-en-ar
  en → ur (response):  Helsinki-NLP/opus-mt-en-ur
  ar → en (user input): Helsinki-NLP/opus-mt-ar-en
  ur → en (user input): Helsinki-NLP/opus-mt-ur-en

HUGGINGFACE FREE TIER:
  Supports ~1000 requests/day. Sufficient for early scale (<5K users).
  When exceeded: self-host MarianMT on VPS (CPU-only, ~500MB RAM).

USER INPUT TRANSLATION (Arabic/Urdu → English BEFORE retrieval):
  If user writes in Arabic or Urdu:
  1. Check L4b cache first (trans_in:{lang}:{md5(text)})
  2. If miss: detect language via character range, translate to English via MarianMT
  3. Cache result in L4b (24 hour TTL)
  4. Perform RAG retrieval in English
  5. Translate AI response back to user's language (check L4 cache first)

RULE: NEVER translate Quran Arabic via AI. Always use the pre-stored verified text.

TRANSLATION FAILURE HANDLING:
  TranslationService never raises exceptions.
  On failure: returns original English text (debate continues uninterrupted).


================================================================================
SECTION 14 — TOKEN BUDGET & RATE LIMITING SYSTEM
================================================================================

PER-USER TOKEN TIERS:
  Tier          | Turns/Day | Max Output Tokens | Model Access          | Est. Cost/User/Month
  --------------|-----------|-------------------|-----------------------|---------------------
  Anonymous     | 5/day     | 600 tokens        | gpt-4o-mini only      | ~$0.25
  Registered    | 20/day    | 800 tokens        | gpt-4o-mini + ltd 4o  | ~$1.00
  Premium       | Unlimited | 1500 tokens       | Full model routing    | ~$5.00

  NOTE: Monthly cost estimates revised to reflect realistic ~3250 token/turn average.

DAILY TURN LIMIT ENFORCEMENT:
  - daily_turn_count tracked on User model
  - Compared against User.daily_reset_date
  - If date changed: reset daily_turn_count to 0
  - Celery beat task resets counts at midnight as a backup

API THROTTLING (DRF):
  - Anonymous:  10 requests/minute (AnonRateThrottle)
  - Registered: 60 requests/minute (UserRateThrottle)

RATE LIMIT RESPONSE:
  HTTP 429 with body: {"error": "Daily limit reached. Register for more turns."}

NOTE ON PREMIUM:
  Premium features are NOT active in initial version (v1).
  All users start as anonymous or registered. Premium tier is built into the
  data model but not exposed in the UI until monetization is enabled.


================================================================================
SECTION 15 — COST MONITORING & BUDGET GUARD
================================================================================

BUDGET GUARD (analytics/budget_guard.py):
  Runs hourly via Celery beat.
  Queries GPTLog for current month's total cost_usd.
  Triggers alerts at 50%, 80%, 100% of MONTHLY_BUDGET_USD.

  At 100%:
  - Writes Redis key 'budget:cutoff_active' = '1' with TTL = seconds to month end
    This flag is read by ALL Gunicorn workers (not in process memory — shared Redis)
  - All new GPT calls return HTTP 503 with explanation
  - Sends email alert to FOUNDER_EMAIL via SMTP (configured in .env)
  - Creates BudgetAlert record with is_cutoff_active=True

  CRITICAL: The flag is in Redis, not settings.py. Using settings.DEBATE_CUTOFF_ACTIVE
  only affects the Celery worker process that runs check(). Gunicorn has separate
  process memory and would never see the flag. Redis solves this.

CELERY BEAT SCHEDULE (defined in settings.py, uses PersistentScheduler):
  - hourly_budget_check: runs every hour at minute=0
  - daily_turn_reset: runs every day at midnight

  IMPORTANT: The Celery Beat systemd service must use:
    --scheduler celery.beat:PersistentScheduler
  NOT django_celery_beat.schedulers:DatabaseScheduler
  (The DatabaseScheduler reads from DB and ignores settings.py CELERY_BEAT_SCHEDULE)

EMAIL ALERTS:
  Budget alerts use send_mail() which reads EMAIL_HOST, EMAIL_PORT,
  EMAIL_HOST_USER, EMAIL_HOST_PASSWORD from Django settings (sourced from .env).
  EMAIL_BACKEND must be 'django.core.mail.backends.smtp.EmailBackend' in production.
  Dev uses console backend (prints to stdout) — set in settings.py based on DEBUG.

ADMIN DASHBOARD METRICS (Django Admin custom view at /admin/dashboard/):
  - Total GPT cost this month vs budget (with % gauge)
  - Cost per debate session (average + outliers)
  - Cache hit rates per layer (L1, L2, L3, L4)
  - Model routing distribution (% gpt-4o-mini vs gpt-4o)
  - Stage progression funnel (how many users reach Stage 2, 3, 4)
  - Daily active users by tier


================================================================================
SECTION 16 — FRONTEND ARCHITECTURE (REACT)
================================================================================

The frontend is a React 18 SPA built with Vite.

ROUTING (React Router v6):
  App.jsx defines routes:
    /           → ChatPage (the main chat interface)
    /login      → AuthPage (Phase 2 — placeholder in v1)
    /settings   → SettingsPage (Phase 2 — placeholder in v1)

  React Router is installed and wired in v1 even though AuthPage and SettingsPage
  are Phase 2 stubs. This prevents future refactoring and makes the login redirect
  in api.js interceptors functional.

STATE MANAGEMENT (Zustand):
  debateStore.js holds:
  - sessionId, messages[], currentStage, debateMode, language
  - isTyping, sidebarOpen
  - sessionHistory[] (populated from API on load for authenticated users)

  Anonymous session persistence:
  - The session_id UUID is returned by the API on first message
  - Stored in Zustand state (in-memory only for anonymous users)
  - On page reload, anonymous users start a new session (by design)
  - Registered users can retrieve previous sessions via GET /debate/sessions/
    which is called on login and populates sessionHistory in the store

API CLIENT (src/services/api.js — Axios):
  - Base URL from VITE_API_URL env var
  - withCredentials: true (for session cookies and auth token cookies)
  - Auth token stored in HttpOnly cookie (set by Django on login — NOT localStorage)
  - 401 interceptor redirects to /login
  - Google OAuth: POSTs access_token to /api/v1/auth/social/google/
    (the correct dj-rest-auth social login endpoint, wired in urls.py)

COMPONENTS (v1 implemented):
  - Navbar.jsx         — Language selector, debate mode dropdown, sign-in button
  - Sidebar.jsx        — New Debate button, session history, trust indicators
  - ChatArea.jsx       — Message list, input bar, typing indicator
  - MarkdownRenderer.jsx — react-markdown with GFM + rehype-sanitize
  - StageProgressBar.jsx — 4-stage progress indicator

COMPONENTS (Phase 2 — stubs only in v1):
  - AuthPage.jsx       — Email/password + Google login form
  - SettingsPage.jsx   — Language/mode preferences
  - ScriptureModal.jsx — Inline scripture lookup popup
  - useAuth.js         — Auth state hook

NO REAL-TIME STREAMING (v1):
  Responses are synchronous (request → typing indicator → response).
  SSE/WebSocket streaming is a Phase 2 feature. The typing indicator provides
  perceived responsiveness during GPT API latency.


================================================================================
SECTION 17 — UI/UX DESIGN SYSTEM & STYLES
================================================================================

DESIGN LANGUAGE: Scholarly, clean, intellectually serious.

COLOR PALETTE:
  --teal:       #0D9488  (primary: CTA buttons, active states, AI avatar)
  --teal-hover: #0F766E  (hover state)
  --teal-dim:   #CCFBF1  (light teal: table headers, code background, badges)
  --teal-pale:  #F0FDF4  (very light teal: even table rows, blockquote background)
  --navy:       #1A1A2E  (headings, strong text, logo)
  --text:       #374151  (body text)
  --text-mid:   #6B7280  (secondary text, metadata)
  --border:     #E5E7EB  (dividers, input borders)

TYPOGRAPHY:
  Body:    Inter, system-ui (14px, 1.75 line-height)
  Headers: Georgia serif for H1, Inter sans for H2/H3
  Arabic:  Noto Naskh Arabic (loaded via Google Fonts or local)
  Code:    Courier New, SF Mono

RTL SUPPORT:
  When language=ar or language=ur, apply dir="rtl" to the markdown container.
  The markdown.css includes RTL overrides for lists, blockquotes, and text alignment.
  The Navbar language selector adds/removes the RTL class on the chat container.

MARKDOWN RENDERING RULES:
  - All AI responses render through MarkdownRenderer (react-markdown)
  - rehype-sanitize prevents XSS in AI-generated HTML
  - Arabic text in backticks renders in Arabic font with warm yellow background
  - Blockquotes used for Quran verse highlights (teal left border, pale background)
  - Tables have overflow-x: auto for mobile compatibility


================================================================================
SECTION 18 — API ENDPOINTS REFERENCE
================================================================================

BASE URL: /api/v1/

AUTH ENDPOINTS (from dj-rest-auth):
  POST /api/v1/auth/login/                  email + password login → returns token in cookie
  POST /api/v1/auth/logout/                 logout → clears cookie
  POST /api/v1/auth/registration/           email registration → returns token in cookie
  POST /api/v1/auth/social/google/          Google OAuth (dj-rest-auth social login)
                                            Body: {"access_token": "google-oauth-token"}
                                            Returns: {"key": "auth-token"} (also set as cookie)
  POST /api/v1/auth/password/change/        change password
  POST /api/v1/auth/password/reset/         forgot password

DEBATE ENDPOINTS:
  POST /api/v1/debate/message/
    Auth: AllowAny (anonymous users supported)
    Throttle: 10/min (anon), 60/min (registered)
    Request:  {
                "message":     "text",           [required, max 2000 chars]
                "session_id":  "uuid",           [optional — omit for new session]
                "language":    "en",             [optional: "en" | "ar" | "ur"]
                "debate_mode": "standard"        [optional — see modes]
              }
    Response: {
                "message_id":    "uuid",
                "content":       "## markdown...",
                "stage":         "existence",
                "session_id":    "uuid",
                "stage_advanced": false          [true if stage progressed this turn]
              }
    Errors:
      400 — Validation error:   {"message": ["..."]}
      400 — Stage locked:       {"error": "...", "stage_locked": true}
      404 — Session not found:  {"error": "Session not found."}
      403 — Not session owner:  {"error": "You do not own this session."}
      429 — Daily limit:        {"error": "Daily limit reached.", "upgrade_required": true}
      429 — Rate limited:       {"detail": "Request was throttled. Expected in Xs."}
      503 — Budget cutoff:      {"error": "Service temporarily paused..."}
      503 — GPT failure:        {"error": "Service temporarily unavailable."}

  GET /api/v1/debate/sessions/
    Auth: Required (IsAuthenticated)
    Response: [{ id, current_stage, debate_mode, detected_persona,
                 god_acceptance, prophecy_acceptance, muhammad_acceptance,
                 created_at, updated_at }]
    NOTE: messages field is EXCLUDED from list view to prevent N+1 loading.
          Use the detail endpoint to get messages for a specific session.

  GET /api/v1/debate/sessions/<session_id>/
    Auth: Required. User must own the session.
    Response: { id, current_stage, debate_mode, detected_persona,
                god_acceptance, prophecy_acceptance, muhammad_acceptance,
                created_at, updated_at,
                messages: [{ id, role, content, stage, citations, created_at }] }

UTILITY:
  GET /health/
    Auth: None
    Response: { "status": "ok", "checks": { "database": "ok", "redis": "ok" } }

RESPONSE CODES:
  200 — Success
  201 — Created (registration)
  400 — Validation error or stage not unlocked
  401 — Authentication required
  403 — Forbidden (not session owner)
  404 — Session not found
  429 — Rate limit or daily turn limit exceeded
  503 — Service temporarily unavailable (budget cutoff or GPT error)


================================================================================
SECTION 19 — INFRASTRUCTURE & DEPLOYMENT ARCHITECTURE
================================================================================

SERVER SPEC (DEVELOPMENT + EARLY PRODUCTION):
  Provider: Hetzner CX21 or DigitalOcean Basic
  CPU: 2 vCPU
  RAM: 4GB
  Storage: 40GB SSD
  OS: Ubuntu 22.04 LTS
  Cost: ~$10–15/month
  Capacity: handles <5,000 users/month comfortably

ALL SERVICES CO-HOSTED ON SINGLE VPS:
  - Nginx (web server + reverse proxy + SSL termination)
  - Gunicorn (4 workers serving Django WSGI)
  - PostgreSQL 15 + pgvector extension
  - Redis 7 (cache + Celery broker + budget flag)
  - Celery Worker (2 concurrent workers — async embedding + analytics)
  - Celery Beat (scheduled tasks — budget check, turn reset)
    Uses PersistentScheduler (NOT DatabaseScheduler)

NGINX CONFIGURATION OVERVIEW:
  - Listen on 80 (redirect to 443)
  - Listen on 443 with SSL (Let's Encrypt / Certbot)
  - Proxy pass /api/ and /admin/ to Gunicorn on 127.0.0.1:8000
  - Serve React dist/ directly from filesystem for all other routes
  - try_files $uri $uri/ /index.html — supports React Router client-side routing
  - Gzip compression enabled
  - FORCE_SCRIPT_NAME is NOT needed — Django is served at root, not a subpath

PROCESS MANAGEMENT (systemd):
  - doesgodexist-django.service  (Gunicorn — 4 workers)
  - doesgodexist-celery.service  (Celery worker — concurrency=2)
  - doesgodexist-beat.service    (Celery beat — PersistentScheduler)

DEPLOYMENT FLOW:
  1. SSH into VPS
  2. git pull origin main
  3. source venv/bin/activate
  4. pip install -r requirements.txt
  5. python manage.py migrate
  6. python manage.py collectstatic --noinput
  7. sudo systemctl restart doesgodexist-django
  8. sudo systemctl restart doesgodexist-celery
  9. sudo systemctl restart doesgodexist-beat

FIRST-TIME DATA LOADING (run once after initial deploy):
  10. python manage.py load_quran [--urdu-file data/quran_urdu.json]
  11. python manage.py load_hadith
  12. python manage.py load_philosophy
  (These trigger Celery embedding tasks automatically)

SSL / HTTPS:
  $ sudo certbot --nginx -d doesgodexist.ai -d www.doesgodexist.ai
  Auto-renew via certbot timer (already configured by certbot).

FRONTEND DEPLOYMENT:
  Build locally: npm run build → creates dist/ folder
  Upload to VPS: scp -r dist/ ubuntu@VPS_IP:/var/www/doesgodexist-frontend/
  Nginx serves dist/ as static files for all non-API routes.


================================================================================
SECTION 20 — SCALING STRATEGY
================================================================================

SCALING TRIGGER POINTS:
  < 5K users/month:    Single VPS ($70–160/month total) — current architecture
  5K–20K:             Separate DB to Hetzner CX31, add 1 more Gunicorn worker ($200–500/month)
  20K–50K:            Managed Postgres (Supabase Free → Pro), Redis Cloud ($500–1000/month)
  50K+:               CDN (Cloudflare), horizontal Django scaling, premium tier mandatory

KEY UPGRADE PATHS:
  - Add SSE/WebSocket streaming when UX demands faster perceived response
  - Add cross-encoder reranker when VPS has budget for CX41 (more RAM for torch)
  - Add Sentry for error tracking when user count warrants
  - Add read replicas for Postgres when DB queries become bottleneck
  - Self-host MarianMT on VPS when HuggingFace free tier is exceeded
  - Move to managed Kubernetes only when team size demands it


================================================================================
SECTION 21 — SECURITY ARCHITECTURE
================================================================================

AUTHENTICATION:
  - django-allauth handles email/password + Google OAuth
  - Auth tokens via dj-rest-auth (stored in HttpOnly cookies — not localStorage)
  - Anonymous users tracked via Django session framework (session_key in DB)
  - Session cookies: Secure=True, HttpOnly=True, SameSite=Lax

SESSION OWNERSHIP:
  ALL views that accept a session_id must verify ownership before proceeding.
  DebateMessageView checks: session.user == request.user OR session.user.session_key
  == request.session.session_key for anonymous users.
  Unauthorized access returns HTTP 403.

API SECURITY:
  - CORS restricted to allowed origins only (django-cors-headers)
  - Rate limiting per user tier prevents abuse
  - Input sanitization via DRF serializers (max_length=2000 on message field)
  - SQL injection impossible — ORM-only queries, no raw SQL in application code
  - XSS protection in frontend via rehype-sanitize on all AI-generated markdown

SENSITIVE DATA:
  - API keys in .env only — never hardcoded, never committed
  - Database passwords in .env
  - Soft-delete only — deleted_at timestamp preserves data integrity

CONTENT MODERATION:
  - GPT system prompt forbids political discussion and sectarian disputes
  - Input length cap (2000 chars) prevents prompt injection attacks
  - Stage gate system prevents users from jumping to sensitive stages

INFRASTRUCTURE:
  - Nginx enforces HTTPS (HTTP → HTTPS redirect)
  - UFW firewall: only ports 80, 443, 22 (SSH) open
  - SSH key-only authentication (password auth disabled on VPS)
  - Gunicorn listens only on 127.0.0.1 (not exposed directly to internet)
  - Redis bound to 127.0.0.1 only (not exposed to internet)
  - Postgres bound to 127.0.0.1 only

DJANGO SECURITY SETTINGS (production):
  SECURE_SSL_REDIRECT = True
  SECURE_HSTS_SECONDS = 31536000
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  X_FRAME_OPTIONS = 'DENY'
  SECURE_CONTENT_TYPE_NOSNIFF = True
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  USE_X_FORWARDED_HOST = True


================================================================================
SECTION 22 — INTEGRATION MAP (ALL SYSTEMS)
================================================================================

  EXTERNAL SERVICES:
  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
  │   OpenAI API    │   │  HuggingFace API  │   │  Google OAuth API    │
  │  GPT-4o-mini    │   │  MarianMT en→ar  │   │  Sign In with Google │
  │  GPT-4o         │   │  MarianMT en→ur  │   │  (dj-rest-auth       │
  │  text-emb-3-sm  │   │  MarianMT ar→en  │   │   social login)      │
  └────────┬────────┘   │  MarianMT ur→en  │   └──────────┬───────────┘
           │            │  (free tier)     │              │
           │            └────────┬─────────┘              │
           │                     │                         │
           ▼                     ▼                         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                       DJANGO APPLICATION                            │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────┐   │
  │  │ GPTClient│  │TranslSvc │  │  allauth     │  │BudgetGuard  │   │
  │  └──────────┘  └──────────┘  └──────────────┘  └─────────────┘   │
  │  ┌──────────────────────────────────────────────────────────────┐  │
  │  │                    DebateOrchestrator                        │  │
  │  │  PersonaDetector → StageValidator → ComplexityRouter         │  │
  │  │  → RetrievalService → PromptBuilder → GPT → StageUpdater    │  │
  │  └──────────────────────────────────────────────────────────────┘  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────┐   │
  │  │DRF Views │  │ Celery   │  │  EmbeddingSvc│  │RetrievalSvc │   │
  │  └──────────┘  └──────────┘  └──────────────┘  └─────────────┘   │
  └────────────────────────────┬────────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌─────────────┐ ┌──────────┐   ┌──────────────┐
        │ PostgreSQL  │ │  Redis   │   │  Celery      │
        │ + pgvector  │ │ L1–L4+   │   │  Worker+Beat │
        │ All tables  │ │ Budget   │   │  Async tasks │
        └─────────────┘ │ Flag     │   └──────────────┘
                        └──────────┘
                                │
                    ┌───────────┘
                    ▼
        ┌──────────────────────────┐
        │     React Frontend       │
        │  Vite SPA / Axios / RTL  │
        │  React Router v6         │
        │  react-markdown / Zustand│
        └──────────────────────────┘

CELERY TASK REGISTRY:
  Task                      | Trigger         | Purpose
  --------------------------|-----------------|-----------------------------------
  embed_chunks              | After ingestion | Batch embed new DocumentChunks
  hourly_budget_check       | Every hour      | Check monthly cost vs budget limit
  daily_turn_reset          | Midnight daily  | Reset User.daily_turn_count

DATA FLOW FOR SINGLE DEBATE TURN:
  1.  User types message → React sends POST /api/v1/debate/message/
  2.  DRF validates input, applies throttle
  3.  View gets or creates anonymous User + DebateSession
  4.  View verifies session ownership
  5.  View checks daily turn limit
  6.  If language != 'en': check L4b cache; if miss, translate to English (MarianMT)
  7.  DebateOrchestrator.run(session, english_message) called
  8.  BudgetGuard checks Redis 'budget:cutoff_active' flag
  9.  StageGateValidator checks current stage is unlocked
  10. PersonaDetector runs (if detected_persona not yet set)
  11. User message saved to DB (seq N)
  12. RetrievalService fetches relevant chunks (L1→L2 cache chain, with is_verified re-check)
  13. PromptBuilder assembles prompt with context + last 6 PRIOR messages (not current)
  14. ComplexityRouter decides gpt-4o-mini vs gpt-4o (uses user turn count only)
  15. GPTClient calls OpenAI API (checks L3 cache first)
  16. Response + GPTLog saved atomically (seq N+1)
  17. Session total_tokens and total_cost_usd updated
  18. StageUpdater checks for acceptance phrases (with negation guard)
  19. If language != 'en': check L4 cache; if miss, translate response back
  20. API returns { content, stage, session_id, message_id, stage_advanced }
  21. React renders markdown response in ChatArea
  22. StageProgressBar updates if stage_advanced=true



