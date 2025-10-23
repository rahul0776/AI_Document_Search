# Testing Checklist

This checklist covers all critical functionality to test before deployment.

## ✅ Pre-Deployment Testing

### 1. Authentication & Authorization

- [ ] **Sign in with dev_login**
  ```bash
  curl -X POST http://localhost:8000/auth/dev_login \
    -H "Content-Type: application/json" \
    -d '{"user_id": "testuser1", "email": "test1@example.com"}'
  ```
  - [ ] Returns JWT token
  - [ ] Token saved in localStorage (check browser DevTools)

- [ ] **Token validation**
  ```bash
  curl http://localhost:8000/me \
    -H "Authorization: Bearer <your-token>"
  ```
  - [ ] Returns user info: `{"user_id": "testuser1", "email": "test1@example.com"}`

- [ ] **401 handling**
  - [ ] Try accessing `/me` without token → 401 error
  - [ ] Frontend clears token and shows "Please sign in"

### 2. Document Upload

- [ ] **Upload PDF**
  - [ ] Choose a PDF file (< 40MB, < 2000 pages)
  - [ ] Upload succeeds
  - [ ] Document appears in library list
  - [ ] Backend logs show: `[UPLOAD] u=testuser1 file=...`
  - [ ] File saved to `backend/data/uploads/testuser1/<doc_id>.pdf`
  - [ ] Metadata created at `backend/data/uploads/testuser1/docs.json`

- [ ] **Background indexing**
  - [ ] Wait 5-10 seconds for indexing
  - [ ] Backend logs show: `[INDEX] begin u=testuser1 doc=...`
  - [ ] Backend logs show: `[INDEX] done u=testuser1 doc=... chunks=N`
  - [ ] FAISS index created at `backend/data/index/testuser1/`

- [ ] **Upload limits**
  - [ ] Try uploading non-PDF → Error: "Only PDF files are supported"
  - [ ] Try uploading PDF > MAX_PDF_MB → Error: "PDF too large"

### 3. Query Functionality

- [ ] **Ask question (streaming)**
  - [ ] Type question in input box
  - [ ] Press "Ask" button
  - [ ] Tokens stream in real-time (word by word)
  - [ ] Answer completes with citations
  - [ ] Citations show format: `{doc_id}... · pN`

- [ ] **Stop streaming**
  - [ ] Press "Ask" button
  - [ ] Press "Stop" button while streaming
  - [ ] Stream stops immediately

- [ ] **Citations**
  - [ ] Click citation chip
  - [ ] PDF panel opens showing correct page
  - [ ] Page number matches citation

- [ ] **Empty query handling**
  - [ ] No documents uploaded → "Please upload a PDF first"
  - [ ] Document still indexing → "Still indexing that PDF"
  - [ ] No relevant results → "I don't know. I couldn't find enough supporting context."

### 4. Scope Toggle

- [ ] **This PDF mode**
  - [ ] Upload a PDF
  - [ ] Ensure "This PDF" is selected
  - [ ] Ask a question specific to that PDF
  - [ ] Answer should only reference that document
  - [ ] Check backend logs: `"scope": "<doc_id>"`

- [ ] **All PDFs mode**
  - [ ] Upload 2+ PDFs
  - [ ] Select "All PDFs" radio button
  - [ ] Ask a question
  - [ ] Answer may reference any uploaded document
  - [ ] Check backend logs: `"scope": "ALL"`

- [ ] **Switch scope**
  - [ ] Ask same question in both modes
  - [ ] Answers may differ based on scope
  - [ ] Citations should match selected scope

### 5. Document Management

- [ ] **List documents**
  - [ ] Upload 3 PDFs
  - [ ] All 3 appear in document library
  - [ ] Shows: filename, pages, upload time
  - [ ] Sorted by upload time (newest first)

- [ ] **Delete document**
  - [ ] Click delete button on a document
  - [ ] Document removed from library
  - [ ] PDF file deleted from `backend/data/uploads/<user_id>/`
  - [ ] Vectors removed from FAISS index
  - [ ] If selected doc deleted → scope switches to "All PDFs"

### 6. Conversation History

- [ ] **History tracking**
  - [ ] Ask 3 questions
  - [ ] All 3 Q&A pairs appear in "Previous answers"
  - [ ] Newest first
  - [ ] Shows timestamp and scope label

- [ ] **Copy conversation**
  - [ ] Click "Copy conversation"
  - [ ] Paste into text editor
  - [ ] Format: `Q: ...\nA: ...\n\n`

- [ ] **Export conversation**
  - [ ] Click "Export conversation"
  - [ ] `conversation.json` downloads
  - [ ] Contains all Q&A with metadata

- [ ] **Export citations**
  - [ ] Ask a question
  - [ ] Click "Export citations"
  - [ ] `citations.json` downloads
  - [ ] Contains doc_id, page, excerpt

### 7. Multi-User Isolation

- [ ] **User 1 setup**
  - [ ] Sign in as `testuser1`
  - [ ] Upload `doc1.pdf`
  - [ ] Ask a question
  - [ ] Note the answer

- [ ] **User 2 setup**
  - [ ] Sign out
  - [ ] Sign in as `testuser2`
  - [ ] Upload `doc2.pdf`
  - [ ] Ask same question

- [ ] **Verify isolation**
  - [ ] User 2 sees only their own documents (not doc1.pdf)
  - [ ] User 2's answer references only doc2.pdf
  - [ ] Check filesystem:
    - `backend/data/uploads/testuser1/` has doc1.pdf
    - `backend/data/uploads/testuser2/` has doc2.pdf
    - `backend/data/index/testuser1/` exists
    - `backend/data/index/testuser2/` exists

- [ ] **Switch users**
  - [ ] Sign back in as `testuser1`
  - [ ] Sees doc1.pdf (not doc2.pdf)
  - [ ] Ask retrieves from doc1.pdf only

### 8. Persistence

- [ ] **Restart backend**
  - [ ] Upload documents and note doc IDs
  - [ ] Stop backend: `docker-compose down` or `Ctrl+C`
  - [ ] Restart: `docker-compose up`
  - [ ] Documents still listed
  - [ ] Ask questions → answers still work
  - [ ] Files still in `data/uploads/`
  - [ ] Indexes still in `data/index/`

### 9. Error Handling

- [ ] **Invalid token**
  - [ ] Clear localStorage token
  - [ ] Try to upload → 401 error
  - [ ] Frontend shows "Please sign in"

- [ ] **Network errors**
  - [ ] Stop backend
  - [ ] Try to ask question → Error message
  - [ ] Restart backend → Works again

- [ ] **Rate limiting**
  - [ ] Send 21 chat requests rapidly (if limit is 20/min)
  - [ ] 21st request → 429 Too Many Requests
  - [ ] Wait 1 minute → Works again

- [ ] **Bad PDF**
  - [ ] Try uploading corrupted PDF
  - [ ] Graceful error message (not 500 crash)

### 10. SSE Streaming

- [ ] **Token in query param**
  - [ ] Open DevTools Network tab
  - [ ] Ask a question
  - [ ] Find `/chat_stream` request
  - [ ] URL includes `?token=<jwt>` parameter
  - [ ] Response type: `text/event-stream`

- [ ] **Heartbeat**
  - [ ] Ask a question with long answer (30+ seconds)
  - [ ] Connection stays alive (no timeout)
  - [ ] Check for `event: ping` in stream (every 15s)

- [ ] **Reconnection**
  - [ ] Ask a question
  - [ ] Close browser tab mid-stream
  - [ ] Backend logs show disconnection
  - [ ] No errors/crashes

### 11. Frontend UI

- [ ] **Sign-in form**
  - [ ] User ID input works
  - [ ] Email input works (optional)
  - [ ] Submit button → token received
  - [ ] Header shows "Signed in as <user_id>"

- [ ] **Upload UI**
  - [ ] "Choose File" button enabled when signed in
  - [ ] Disabled when not signed in
  - [ ] Shows "Working..." during upload
  - [ ] Success message after upload

- [ ] **Ask UI**
  - [ ] Input disabled when not signed in
  - [ ] "Ask" button disabled when no question
  - [ ] "Stop" button appears during streaming
  - [ ] Answer box shows "..." while streaming

- [ ] **Document library**
  - [ ] Shows all user's documents
  - [ ] Highlights selected document
  - [ ] Delete button works
  - [ ] Refreshes after upload

- [ ] **PDF viewer**
  - [ ] Opens when citation clicked
  - [ ] Shows correct page
  - [ ] Close button works
  - [ ] Navigation works (prev/next page)

### 12. Configuration

- [ ] **Environment variables loaded**
  ```bash
  # Check backend reads .env
  docker-compose exec backend env | grep OPENAI_API_KEY
  docker-compose exec backend env | grep AUTH_JWT_SECRET
  ```

- [ ] **Settings applied**
  - [ ] Check `MAX_PDF_MB` limit enforced
  - [ ] Check `MAX_PAGES` limit enforced
  - [ ] Check `TOP_K_DEFAULT` in retrieval
  - [ ] Check CORS allows `FRONTEND_ORIGIN`

### 13. Docker Deployment

- [ ] **Build succeeds**
  ```bash
  docker-compose build
  ```
  - [ ] Backend builds without errors
  - [ ] Frontend builds without errors

- [ ] **Containers start**
  ```bash
  docker-compose up -d
  ```
  - [ ] Backend container running
  - [ ] Frontend container running
  - [ ] Health checks pass

- [ ] **Volumes mounted**
  ```bash
  docker-compose exec backend ls /app/data/uploads
  docker-compose exec backend ls /app/data/index
  ```
  - [ ] Directories exist
  - [ ] Files persist after restart

- [ ] **Networking**
  - [ ] Frontend can reach backend
  - [ ] CORS configured correctly
  - [ ] Static files served

### 14. Production Configuration

- [ ] **Security settings**
  - [ ] `DEV_NO_AUTH=0` in production .env
  - [ ] Strong `AUTH_JWT_SECRET` (32+ chars)
  - [ ] `OPENAI_API_KEY` not hardcoded

- [ ] **Nginx proxy (if using)**
  - [ ] Frontend served at `/`
  - [ ] Backend proxied at `/api/` or direct routes
  - [ ] SSE/WebSocket headers configured
  - [ ] `client_max_body_size` sufficient for uploads

- [ ] **HTTPS/SSL (production only)**
  - [ ] Certificates installed
  - [ ] HTTP redirects to HTTPS
  - [ ] Security headers present

---

## 🐛 Common Issues & Fixes

### Issue: "401 Unauthorized" on all requests
**Fix:** Check token is saved in localStorage and included in requests

### Issue: Streaming doesn't work
**Fix:** 
1. Check frontend sends `token` as query param
2. Check backend has `get_current_user_query` 
3. Check Nginx proxy has WebSocket/SSE headers

### Issue: Documents not persisting after restart
**Fix:** Check Docker volumes are mounted correctly in docker-compose.yml

### Issue: User sees other users' documents
**Fix:** Check `IndexRegistry.for_user()` and `uploads_dir_for()` use correct user_id

### Issue: Upload fails silently
**Fix:** Check backend logs for errors, verify file size/type limits

---

## ✅ Sign-Off

After completing all checks:

- [ ] All authentication tests passed
- [ ] All upload/indexing tests passed
- [ ] All query/chat tests passed
- [ ] Multi-user isolation verified
- [ ] Persistence verified
- [ ] Error handling verified
- [ ] Docker deployment verified
- [ ] Production configuration verified

**Tested by:** _______________  
**Date:** _______________  
**Environment:** ☐ Development  ☐ Staging  ☐ Production  
**Version/Commit:** _______________  

**Notes:**
```
[Add any issues found or special configurations needed]
```

---

**Ready for deployment? 🚀**

