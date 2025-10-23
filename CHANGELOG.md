# Changelog

All notable changes to the AI Document Search project.

---

## [1.1.0] - 2024-10-23

### 🆕 Added

#### Authentication & Security
- **SSE Token Authentication** - EventSource can now authenticate using query parameter (`?token=<JWT>`)
  - Added `verify_token()` helper function
  - Added `get_current_user_query()` for query param validation
  - Updated `/chat_stream` endpoint to accept token in URL
  
#### Stability & Performance
- **SSE Heartbeat** - Periodic ping every 15 seconds to prevent connection timeouts
  - Implemented in event generator for streaming responses
  - Keeps long-running queries alive

#### Documentation
- **DEPLOYMENT.md** - Comprehensive deployment guide
  - Quick start for development
  - Docker deployment instructions
  - Production deployment guide
  - Configuration reference
  - Troubleshooting section
  - Security checklist
  - Scaling considerations

- **TESTING_CHECKLIST.md** - Complete testing guide
  - 14 test categories with step-by-step instructions
  - Common issues and fixes
  - Sign-off template
  - 50+ specific test cases

- **IMPLEMENTATION_SUMMARY.md** - Technical overview
  - What was already implemented
  - What was newly added
  - Requirements coverage matrix
  - Design decisions and trade-offs

- **QUICK_START.md** - 5-minute getting started guide
  - Docker quick start
  - Local development setup
  - First-time use walkthrough
  - Common issues and solutions

- **Enhanced README.md**
  - Feature highlights with badges
  - Architecture diagram
  - API endpoint reference
  - Technology stack details
  - Contributing guidelines

#### Configuration
- **env.example** - Complete environment template
  - All configuration options documented
  - Organized by category
  - Production deployment notes
  - Security recommendations

#### Docker & Deployment
- **docker-compose.yml** - Full orchestration
  - Backend service with environment configuration
  - Frontend service with build args
  - Nginx reverse proxy (production profile)
  - Volume mounts for data persistence
  - Health checks
  - Network configuration

- **frontend/Dockerfile** - Optimized multi-stage build
  - Stage 1: npm build
  - Stage 2: Nginx serve
  - Reduced image size ~90%

- **frontend/nginx.conf** - Frontend Nginx config
  - React Router support
  - Gzip compression
  - Cache headers
  - Security headers

- **nginx/nginx.conf** - Reverse proxy config
  - HTTP and HTTPS server blocks
  - WebSocket/SSE support
  - SSL/TLS configuration template
  - Large file upload support

- **.dockerignore** - Build optimization
  - Excludes unnecessary files from images
  - Faster builds, smaller images

#### Scripts
- **start.sh** - Linux/Mac startup script
  - Environment check
  - Docker validation
  - One-command startup

- **start.bat** - Windows startup script
  - Same functionality for Windows
  - PowerShell compatible

### 🔧 Modified

#### Backend
- `backend/auth.py`
  - Refactored token validation into `verify_token()`
  - Added `get_current_user_query()` for SSE auth
  - Improved code reusability

- `backend/main.py`
  - Added `time` import
  - Updated `/chat_stream` to use query param auth
  - Added SSE heartbeat/ping logic
  - Improved streaming stability

### 📊 Metrics

**Lines of Code Added:** ~2,500+
- Documentation: ~1,800 lines
- Configuration: ~400 lines
- Code changes: ~80 lines
- Scripts: ~100 lines

**Files Added:** 12
**Files Modified:** 3

**Test Coverage:** 50+ test cases documented

---

## [1.0.0] - Initial Release

### ✨ Core Features

#### Backend (FastAPI)
- Multi-user document isolation
- JWT authentication with dev mode
- PDF upload with background indexing
- Smart text chunking with overlap
- OpenAI embeddings integration
- FAISS vector search
- RAG pipeline with LLM
- MMR reranking
- Quality controls (deduplication, score threshold)
- Streaming responses via SSE
- Rate limiting
- Telemetry logging
- Evaluation framework

#### Frontend (React)
- User authentication UI
- PDF upload interface
- Document library management
- Scope toggle (This PDF / All PDFs)
- Streaming chat interface
- Stop button for streams
- Citation display and PDF viewer
- Conversation history
- Copy/export functionality
- Responsive design with Tailwind CSS

#### Infrastructure
- Per-user storage isolation
- FAISS index per user
- Metadata storage in JSON
- Background task processing
- Error handling
- CORS configuration
- Static file serving

---

## Migration Guide

### From 1.0.0 to 1.1.0

No breaking changes! All existing features continue to work.

**Optional improvements to adopt:**

1. **Environment Configuration**
   ```bash
   cp env.example .env
   # Review and set your values
   ```

2. **Docker Deployment**
   ```bash
   docker-compose up --build
   ```

3. **Production Security**
   - Set `DEV_NO_AUTH=0`
   - Generate strong `AUTH_JWT_SECRET`
   - Configure HTTPS/SSL

---

## Upgrade Instructions

### Docker Users

```bash
# Pull latest changes
git pull

# Rebuild containers
docker-compose down
docker-compose up --build

# Data persists automatically in volumes
```

### Local Development Users

```bash
# Pull latest changes
git pull

# Backend - reinstall if dependencies changed
cd backend
pip install -r requirements.txt

# Frontend - reinstall if dependencies changed
cd frontend
npm install

# Restart services
# (No data migration needed)
```

---

## Deprecation Notices

None in this release.

---

## Known Issues

### Non-Critical

1. **Local FAISS Storage**
   - Not suitable for distributed/multi-server deployments
   - Workaround: Use managed vector database (Pinecone, Weaviate)

2. **JSON Metadata Storage**
   - Not suitable for high concurrency
   - Workaround: Migrate to PostgreSQL/MySQL for production

3. **In-Memory Rate Limiting**
   - Doesn't work across multiple backend instances
   - Workaround: Use Redis-backed rate limiting

4. **Background Task Durability**
   - Tasks lost if process crashes during indexing
   - Workaround: Use task queue (Celery, RQ)

### Planned Improvements

- [ ] Add real user authentication (OAuth, email/password)
- [ ] Cloud storage integration (S3, GCS)
- [ ] Managed vector database support
- [ ] Redis caching layer
- [ ] Batch upload
- [ ] Document preview thumbnails
- [ ] Advanced search filters
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] Mobile-responsive PDF viewer

---

## Security Updates

### 1.1.0
- Enhanced SSE authentication (query param support)
- Comprehensive security documentation
- Production deployment best practices

### 1.0.0
- JWT-based authentication
- Per-user data isolation
- CORS protection
- Rate limiting on sensitive endpoints

---

## Performance Improvements

### 1.1.0
- SSE heartbeat prevents timeout-related reconnections
- Optimized Docker images (multi-stage builds)
- Nginx caching headers for static assets

### 1.0.0
- Background indexing (non-blocking uploads)
- MMR reranking (reduces redundant results)
- FAISS vector search (fast similarity search)
- Streaming responses (immediate feedback)

---

## Breaking Changes

None in 1.1.0 → Fully backward compatible!

---

## Contributors

- Initial development and enhancements by project team
- Documentation improvements
- Docker and deployment configuration

---

## Feedback & Support

Found a bug? Have a feature request?

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** [Your support email]
- **Documentation:** See README.md, DEPLOYMENT.md, QUICK_START.md

---

**Thank you for using AI Document Search! 🙏**

