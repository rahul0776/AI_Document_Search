# Quick Start Guide 🚀

Get your AI Document Search up and running in 5 minutes!

---

## Option 1: Docker (Easiest) 🐳

### Prerequisites
- Docker Desktop installed and running
- OpenAI API key

### Steps

1. **Clone and navigate:**
```bash
cd AI_Document_Search
```

2. **Set up environment:**
```bash
# Copy template
cp env.example .env

# Edit .env and add your OpenAI API key
notepad .env   # Windows
nano .env      # Linux/Mac
```

Set at minimum:
```bash
OPENAI_API_KEY=sk-your-key-here
```

3. **Start everything:**
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# Or manually
docker-compose up --build
```

4. **Open your browser:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

5. **Test it out:**
   - Sign in with any user ID (e.g., "demo")
   - Upload a PDF
   - Wait ~10 seconds for indexing
   - Ask a question!

---

## Option 2: Local Development 💻

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (new terminal)

```bash
cd frontend

# Install dependencies
npm install

# Create .env
echo "REACT_APP_API_BASE=http://localhost:8000" > .env

# Run development server
npm start
```

### Access
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## First Time Use 👤

1. **Sign In (Dev Mode)**
   - User ID: `demo` (or any name)
   - Email: (optional)
   - Click "Sign in"

2. **Upload a PDF**
   - Click "Choose File"
   - Select a PDF (< 40MB)
   - Wait for "Uploaded" message

3. **Wait for Indexing**
   - Background process takes 5-30 seconds
   - Depends on PDF size

4. **Ask a Question**
   - Type your question
   - Press "Ask"
   - Watch the answer stream in!

5. **View Citations**
   - Click any citation chip
   - PDF opens to that page

---

## Common Issues 🔧

### "401 Unauthorized"
- Sign in first using the form in the header
- Check that token is saved (browser DevTools → Application → Local Storage)

### "Please upload a PDF first"
- You haven't uploaded any documents yet
- Upload a PDF and wait for indexing

### "Still indexing that PDF"
- Background indexing in progress
- Wait 10-30 seconds and try again

### Docker won't start
- Make sure Docker Desktop is running
- Check no other services are using port 3000 or 8000

### Upload fails
- Check PDF is < 40MB
- Check PDF is valid (not corrupted)
- Check backend logs: `docker-compose logs backend`

---

## What to Try 🎯

### Basic Features
- ✅ Upload multiple PDFs
- ✅ Ask questions across all PDFs ("All PDFs" mode)
- ✅ Ask questions about specific PDF ("This PDF" mode)
- ✅ Click citations to view source pages
- ✅ Copy/export conversation
- ✅ Delete documents

### Multi-User
- ✅ Sign out
- ✅ Sign in as different user
- ✅ Upload different documents
- ✅ Verify users can't see each other's docs

### Persistence
- ✅ Upload docs
- ✅ Stop backend: `docker-compose down`
- ✅ Restart: `docker-compose up`
- ✅ Docs still there!

---

## Configuration ⚙️

### Basic Settings (in .env)

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (with defaults)
MAX_PDF_MB=40                          # Max PDF size
MAX_PAGES=2000                         # Max pages per PDF
EMBED_MODEL=text-embedding-3-small     # Embedding model
CHAT_MODEL=gpt-4o-mini                 # Chat model
TOP_K_DEFAULT=5                        # Results per query

# Development
DEV_NO_AUTH=1                          # 0 in production
AUTH_JWT_SECRET=devsecret              # Change in production!
```

See `env.example` for all options.

---

## Production Deployment 🌐

For production use:

1. **Security:**
```bash
DEV_NO_AUTH=0
AUTH_JWT_SECRET=<generate-strong-random-32+-char-string>
```

2. **Deploy with Nginx:**
```bash
docker-compose --profile production up -d
```

3. **Configure SSL/TLS:**
- Add certificates to `nginx/ssl/`
- Edit `nginx/nginx.conf` (uncomment HTTPS section)

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

---

## Testing Checklist ✅

Before deploying to production, verify:

- [ ] Multiple users can sign in
- [ ] Each user sees only their own documents
- [ ] Upload works (< 40MB PDFs)
- [ ] Indexing completes in background
- [ ] Questions return relevant answers
- [ ] Citations link to correct pages
- [ ] Streaming works (tokens appear one by one)
- [ ] Stop button works during streaming
- [ ] Delete removes documents
- [ ] Restart persists data

See [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) for detailed tests.

---

## Getting Help 💬

### View Logs

**Docker:**
```bash
docker-compose logs -f              # All services
docker-compose logs -f backend      # Backend only
docker-compose logs -f frontend     # Frontend only
```

**Local:**
- Backend: Terminal running uvicorn
- Frontend: Terminal running npm + browser console

### Check Health

```bash
curl http://localhost:8000/health   # Backend
curl http://localhost:3000/health   # Frontend
```

### Documentation
- [README.md](README.md) - Full documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) - Testing guide
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

---

## Architecture Overview 🏗️

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐      ┌──────────────┐
│  React Frontend │─────▶│   FastAPI    │
│  (Port 3000)    │◀─────│   Backend    │
└─────────────────┘      │  (Port 8000) │
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                ┌──────┐   ┌───────┐   ┌────────┐
                │ FAISS│   │OpenAI │   │ PDFs   │
                │ Index│   │  API  │   │ Storage│
                └──────┘   └───────┘   └────────┘
```

**Flow:**
1. User uploads PDF → Saved to `data/uploads/<user_id>/`
2. Background task extracts text → Chunks it → Embeds it
3. Embeddings stored in FAISS index at `data/index/<user_id>/`
4. User asks question → Embedded → Searched in FAISS
5. Top chunks retrieved → Sent to OpenAI with question
6. Answer streamed back with citations

---

## Next Steps 📚

1. ✅ Get it running (you are here!)
2. 📖 Read [README.md](README.md) for features
3. 🧪 Run through [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
4. 🚀 Deploy with [DEPLOYMENT.md](DEPLOYMENT.md)
5. 🎨 Customize for your use case
6. 🌟 Star the repo if you like it!

---

**Happy searching! 🔍✨**

