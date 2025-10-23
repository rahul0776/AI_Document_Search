# Deployment Guide - AI Document Search

This guide covers how to deploy the AI Document Search application in various environments.

## Table of Contents
- [Quick Start (Development)](#quick-start-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_BASE=http://localhost:8000" > .env

# Run frontend
npm start
```

### 3. Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### 1. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit .env and set required values:
# - OPENAI_API_KEY (required)
# - AUTH_JWT_SECRET (generate a strong random string)
# - DEV_NO_AUTH=0 (for production)
```

### 2. Start Services
```bash
# Development mode (with hot reload)
docker-compose up --build

# Production mode (with Nginx reverse proxy)
docker-compose --profile production up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Data Persistence
Data is persisted in the following directories:
- `backend/data/uploads/` - User-uploaded PDFs
- `backend/data/index/` - FAISS vector indexes
- `backend/data/logs/` - Telemetry and event logs

These directories are mounted as volumes in Docker Compose.

---

## Production Deployment

### Option 1: Docker Compose with Nginx

1. **Set up environment variables:**
```bash
cp env.example .env
nano .env  # Edit configuration
```

Required production settings:
```bash
DEV_NO_AUTH=0
AUTH_JWT_SECRET=<generate-strong-random-string>
OPENAI_API_KEY=sk-your-real-key
FRONTEND_ORIGIN=https://yourdomain.com
REACT_APP_API_BASE=https://yourdomain.com/api
```

2. **Configure SSL/TLS:**
```bash
# Place SSL certificates in nginx/ssl/
mkdir -p nginx/ssl
# Copy your certificates:
# - nginx/ssl/fullchain.pem
# - nginx/ssl/privkey.pem
```

3. **Update Nginx configuration:**
Edit `nginx/nginx.conf` and uncomment the HTTPS server block. Update `server_name` to your domain.

4. **Start services:**
```bash
docker-compose --profile production up -d
```

5. **Set up automatic SSL renewal (Let's Encrypt):**
```bash
# Add certbot service to docker-compose.yml
# See: https://certbot.eff.org/docs/using.html#running-with-docker
```

### Option 2: Separate Hosting

**Backend:**
- Deploy to any Python hosting (AWS EC2, DigitalOcean, Heroku, etc.)
- Install dependencies: `pip install -r requirements.txt`
- Set environment variables
- Run: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`

**Frontend:**
- Build: `npm run build`
- Deploy `build/` folder to any static hosting (Netlify, Vercel, S3+CloudFront, etc.)
- Set `REACT_APP_API_BASE` to your backend URL

**Database/Storage:**
- Mount persistent storage for `data/` directory
- Consider using cloud storage (S3, Google Cloud Storage) for uploads
- Consider using managed vector database (Pinecone, Weaviate) instead of local FAISS

---

## Configuration

### Environment Variables

See `env.example` for all available options. Key settings:

#### Authentication
- `AUTH_JWT_SECRET`: Secret key for JWT signing (required in production)
- `DEV_NO_AUTH`: Set to `0` in production, `1` for development

#### OpenAI
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `EMBED_MODEL`: Embedding model (default: `text-embedding-3-small`)
- `CHAT_MODEL`: Chat model (default: `gpt-4o-mini`)

#### Application
- `MAX_PDF_MB`: Maximum PDF size in MB (default: 40)
- `MAX_PAGES`: Maximum pages per PDF (default: 2000)
- `TOP_K_DEFAULT`: Number of retrieval results (default: 5)

#### CORS
- `FRONTEND_ORIGIN`: Allowed frontend origins (comma-separated)

### Per-User Isolation

The application automatically isolates users:
- Uploads: `data/uploads/<user_id>/`
- Indexes: `data/index/<user_id>/`
- Each user can only access their own documents

### Rate Limiting

Default rate limits (configurable in `backend/middleware/ratelimit.py`):
- Chat endpoints: 20 requests/minute per user
- Can be customized per endpoint

---

## Troubleshooting

### Common Issues

**1. SSE/Streaming not working**
- Check that Nginx is configured for WebSocket/SSE (`proxy_http_version 1.1`)
- Verify `proxy_read_timeout` is sufficient (300s recommended)
- Ensure frontend sends `token` as query parameter

**2. 401 Unauthorized errors**
- Check that JWT token is valid and not expired
- Verify `AUTH_JWT_SECRET` matches between backend and token generation
- In development, set `DEV_NO_AUTH=1` to bypass auth

**3. PDF upload fails**
- Check `MAX_PDF_MB` setting
- Verify Nginx `client_max_body_size` is sufficient
- Check disk space in upload directory

**4. Embeddings/Chat not working**
- Verify `OPENAI_API_KEY` is set and valid
- Check OpenAI API quota/billing
- Review backend logs for error messages

**5. FAISS index errors**
- Ensure `data/index/` directory is writable
- Check for sufficient disk space
- Delete corrupted index: `rm -rf data/index/<user_id>/`

**6. CORS errors**
- Add frontend URL to `FRONTEND_ORIGIN` in .env
- Check that backend CORS middleware is configured correctly

### Viewing Logs

**Docker:**
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

**Local development:**
- Backend: Terminal running uvicorn
- Frontend: Browser console + terminal running npm start
- Application logs: `backend/data/logs/events.jsonl`

### Health Checks

**Backend:**
```bash
curl http://localhost:8000/health
# Should return: {"ok": true}
```

**Frontend:**
```bash
curl http://localhost:3000/health
# Should return: OK
```

### Resetting the Application

**Clear all data:**
```bash
# Stop services
docker-compose down

# Remove data directories
rm -rf backend/data/uploads/*
rm -rf backend/data/index/*
rm -rf backend/data/logs/*

# Restart
docker-compose up -d
```

**Reset specific user:**
```bash
rm -rf backend/data/uploads/<user_id>
rm -rf backend/data/index/<user_id>
```

---

## Security Checklist

For production deployment:

- [ ] Set `DEV_NO_AUTH=0`
- [ ] Generate strong `AUTH_JWT_SECRET` (32+ random characters)
- [ ] Use HTTPS/TLS (configure SSL certificates)
- [ ] Set restrictive CORS origins
- [ ] Enable firewall rules (allow only 80/443)
- [ ] Keep `OPENAI_API_KEY` secret (use environment variables, not code)
- [ ] Set up log rotation for `data/logs/`
- [ ] Configure backups for `data/uploads/` and `data/index/`
- [ ] Monitor API usage and set up alerts
- [ ] Review and adjust rate limits
- [ ] Keep dependencies updated (`pip upgrade`, `npm update`)

---

## Scaling Considerations

For high-traffic production:

1. **Backend:**
   - Increase Uvicorn workers: `WORKERS=4` (or more)
   - Use load balancer (Nginx, HAProxy, AWS ALB)
   - Consider async task queue (Celery, RQ) for indexing

2. **Storage:**
   - Move to cloud storage (S3, GCS) for uploads
   - Use managed vector database (Pinecone, Weaviate)
   - Implement caching (Redis) for embeddings

3. **Database:**
   - Move metadata to PostgreSQL/MySQL instead of JSON files
   - Use connection pooling

4. **Monitoring:**
   - Set up APM (New Relic, Datadog, Sentry)
   - Monitor OpenAI API usage and costs
   - Track response times and error rates

---

## Support

For issues and questions:
- GitHub Issues: [Your repository]
- Documentation: [Your docs site]
- Email: [Your support email]

