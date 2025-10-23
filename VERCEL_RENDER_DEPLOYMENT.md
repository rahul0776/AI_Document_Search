# 🚀 Deploy to Vercel + Render (100% FREE)

## ✅ Why This Combo is Perfect

- ✅ **Completely FREE** - No credit card needed
- ✅ **Professional** - Used by top companies
- ✅ **Fast** - Vercel has global edge CDN
- ✅ **Reliable** - Both platforms are stable
- ✅ **Custom domains** - Free HTTPS included

---

## 📋 Deployment Steps (25 Minutes)

### **Part 1: Deploy Backend to Render (15 min)**

#### **Step 1: Sign Up for Render (2 min)**

1. Go to **https://render.com**
2. Click **"Get Started"**
3. Choose **"Sign up with GitHub"**
4. Authorize Render

---

#### **Step 2: Create Web Service (2 min)**

1. Click **"New +"** → **"Web Service"**
2. Click **"Connect GitHub"**
3. Find and select **"AI_Document_Search"**
4. Click **"Connect"**

---

#### **Step 3: Configure Backend (5 min)**

Fill in these settings:

**Basic Settings:**
- **Name**: `ai-doc-backend` (or your preferred name)
- **Region**: Choose closest to you (e.g., Oregon, Frankfurt)
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

**Advanced Settings:**
- **Plan**: Select **"Free"** (important!)
- **Auto-Deploy**: **Yes** (so git push = auto deploy)

---

#### **Step 4: Add Environment Variables (3 min)**

Scroll down to **"Environment Variables"** section.

Click **"Add Environment Variable"** for each:

```bash
Key: OPENAI_API_KEY
Value: sk-proj-your-actual-key-here

Key: AUTH_JWT_SECRET
Value: your-secret-key-at-least-32-characters-long

Key: DEV_NO_AUTH
Value: 0

Key: PYTHON_VERSION
Value: 3.11.0
```

**IMPORTANT:** Keep these secret! Don't share them.

---

#### **Step 5: Deploy Backend (3 min)**

1. Click **"Create Web Service"** at the bottom
2. Render will start building your backend
3. Watch the logs - you'll see:
   - Installing dependencies...
   - Starting server...
   - ✅ "Your service is live"

**Your backend URL will be:**
```
https://ai-doc-backend.onrender.com
```

**Copy this URL!** You'll need it for the frontend.

---

#### **Step 6: Test Backend (1 min)**

Open in browser or use curl:
```bash
curl https://ai-doc-backend.onrender.com/health

# Should return: {"ok":true}
```

✅ If you see `{"ok":true}`, your backend is live!

---

### **Part 2: Deploy Frontend to Vercel (10 min)**

#### **Step 1: Sign Up for Vercel (2 min)**

1. Go to **https://vercel.com**
2. Click **"Sign Up"**
3. Choose **"Continue with GitHub"**
4. Authorize Vercel

---

#### **Step 2: Import Project (2 min)**

1. Click **"Add New..."** → **"Project"**
2. Find **"AI_Document_Search"**
3. Click **"Import"**

---

#### **Step 3: Configure Frontend (3 min)**

**Framework Preset:**
- Vercel should auto-detect: **"Create React App"**
- If not, select it manually

**Root Directory:**
- Click **"Edit"** next to Root Directory
- Enter: `frontend`
- Click **"Continue"**

**Build Settings:**
- Build Command: `npm run build` (auto-filled)
- Output Directory: `build` (auto-filled)
- Install Command: `npm install` (auto-filled)

---

#### **Step 4: Add Environment Variable (2 min)**

Click **"Environment Variables"** section.

Add this variable:

```bash
Name: REACT_APP_API_BASE
Value: https://ai-doc-backend.onrender.com
```

**IMPORTANT:** 
- Replace with YOUR actual Render backend URL
- No trailing slash!
- Must include `https://`

---

#### **Step 5: Deploy Frontend (1 min)**

1. Click **"Deploy"**
2. Vercel will build your frontend
3. Wait 2-3 minutes
4. ✅ You'll see "Congratulations!"

**Your frontend URL will be:**
```
https://ai-document-search.vercel.app
```

(Vercel generates a unique URL based on your repo name)

---

#### **Step 6: Test Your Live App! (2 min)**

1. Click **"Visit"** or open your Vercel URL
2. You should see your login page!
3. Try creating an account
4. Upload a PDF
5. Test the chat

🎉 **Congratulations! Your app is LIVE!**

---

## 🔧 Important: Update CORS

Your backend needs to allow requests from your Vercel frontend.

### **Update backend/main.py**

Find the `CORSMiddleware` section and update it:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-document-search.vercel.app",  # Your Vercel URL
        "http://localhost:3000",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After updating:**
```bash
git add backend/main.py
git commit -m "fix: Update CORS for Vercel deployment"
git push origin main
```

Render will auto-redeploy with the new CORS settings!

---

## 🎨 Get a Custom Domain (Optional)

### **For Vercel (Frontend)**

1. Go to your project in Vercel
2. Click **"Settings"** → **"Domains"**
3. Enter your domain: `ai-docs.yourdomain.com`
4. Vercel will show you DNS records to add
5. Add CNAME record at your domain provider
6. Wait 5-10 minutes

### **For Render (Backend)**

1. Go to your service in Render
2. Click **"Settings"** → **"Custom Domain"**
3. Enter: `api.yourdomain.com`
4. Add CNAME record shown
5. Update frontend env var with new backend URL

---

## 💰 Cost Breakdown

### **Completely FREE!**

| Service | Cost | Limits |
|---------|------|--------|
| **Render** | $0 | 750 hours/month, sleeps after 15 min idle |
| **Vercel** | $0 | 100 GB bandwidth, unlimited sites |
| **Total** | **$0/month** | Perfect for demos! |

**Note:** Render free tier sleeps after 15 min of inactivity. First request after sleep takes 30-60 seconds to wake up. This is fine for demos!

---

## 🐛 Troubleshooting

### **Issue: "Cannot connect to backend"**

**Check:**
1. Is backend URL correct in Vercel env var?
2. Does it include `https://`?
3. No trailing slash?

**Fix:**
```bash
# In Vercel dashboard:
REACT_APP_API_BASE=https://ai-doc-backend.onrender.com
# (not: http://, not: /api, no trailing slash!)
```

Then redeploy Vercel.

---

### **Issue: "CORS error"**

**Symptom:** See error in browser console about CORS

**Fix:** Update `backend/main.py` with your Vercel URL (see CORS section above)

---

### **Issue: "Backend is slow/timing out"**

**Cause:** Render free tier sleeps after 15 min idle

**Expected behavior:**
- First request after sleep: 30-60 seconds
- Subsequent requests: Fast (<2s)

**Solutions:**
1. **Acceptable for demos** - just mention it when sharing
2. **Ping service** - Set up UptimeRobot to ping every 5 min (keeps it awake)
3. **Upgrade** - Pay $7/month for Render to stay always-on

---

### **Issue: "Module not found" errors**

**Check:**
1. Are all dependencies in `requirements.txt`?
2. Is Python version correct?

**Fix:**
```bash
# Regenerate requirements
cd backend
pip freeze > requirements.txt
git add requirements.txt
git commit -m "fix: Update requirements"
git push
```

---

## 📊 Monitor Your Deployments

### **Render Dashboard**

- **Logs**: See real-time backend logs
- **Metrics**: CPU, Memory usage
- **Events**: Deployment history

### **Vercel Dashboard**

- **Deployments**: See build history
- **Analytics**: Page views, performance
- **Logs**: Frontend build logs

### **Check Costs**

- **OpenAI Usage**: https://platform.openai.com/usage
- Set up billing alerts!

---

## 🎯 After Deployment Checklist

- [ ] Backend is live and returns `{"ok":true}` on `/health`
- [ ] Frontend is live and shows login page
- [ ] Can create an account
- [ ] Can login
- [ ] Can upload PDF
- [ ] Can chat with PDF
- [ ] CORS is configured correctly
- [ ] Updated README with live links
- [ ] Posted on LinkedIn
- [ ] Added to resume

---

## 📝 Update Your README

Add this to the top of your README.md:

```markdown
# 🚀 AI Document Search

**[🔗 Live Demo](https://ai-document-search.vercel.app)** | 
**[💻 GitHub](https://github.com/rahul0776/AI_Document_Search)**

> **Try it live!** No installation needed: https://ai-document-search.vercel.app

A production-ready RAG application enabling intelligent conversations with PDF documents.

---
```

Commit and push:
```bash
git add README.md
git commit -m "docs: Add live demo link"
git push origin main
```

---

## 🎓 What This Demonstrates

**To hiring managers, this shows:**

✅ **Full-Stack Deployment** - Can deploy both frontend and backend  
✅ **Cloud Infrastructure** - Understands modern hosting platforms  
✅ **CI/CD** - Git push triggers auto-deployment  
✅ **Environment Management** - Proper use of env variables  
✅ **CORS & Security** - Understands web security basics  
✅ **Professional Practices** - Uses industry-standard tools  

---

## 📱 Share Your Live App

### **LinkedIn Post**

```
🚀 Excited to share my AI Document Search platform - now LIVE!

Try it here: https://ai-document-search.vercel.app

Built with:
• FastAPI backend on Render
• React frontend on Vercel  
• Advanced RAG with hybrid search
• Real-time streaming with GPT-4
• Secure authentication & dark mode

100% free deployment, production-ready architecture.

Code: https://github.com/rahul0776/AI_Document_Search

#AI #WebDevelopment #Python #React #FullStack
```

### **Resume**

```
AI Document Search Platform
Live: https://ai-document-search.vercel.app
GitHub: github.com/rahul0776/AI_Document_Search

• Deployed production RAG application to Vercel (frontend) and 
  Render (backend) with automated CI/CD pipelines
• Implemented secure environment-based configuration across 
  development and production environments
• Configured CORS, HTTPS, and API authentication for secure 
  cross-origin communication
```

### **Email Signature**

```
Rahul Lotlikar | Software Engineer
📧 lucifert75@gmail.com
💼 linkedin.com/in/rahul-lotlikar
🚀 Live Project: ai-document-search.vercel.app
💻 GitHub: github.com/rahul0776
```

---

## 🔄 Redeploy / Update

### **Backend (Render)**

Automatic! Just:
```bash
git push origin main
```

Render auto-detects and redeploys.

### **Frontend (Vercel)**

Automatic! Just:
```bash
git push origin main
```

Vercel auto-detects and redeploys.

**Both platforms support instant rollback if something breaks!**

---

## 💡 Pro Tips

1. **Test locally first**: Always test changes locally before pushing
2. **Monitor logs**: Check Render and Vercel dashboards for errors
3. **Set up alerts**: Enable email notifications for failed deployments
4. **Use branches**: Create `dev` branch for testing, `main` for production
5. **Document everything**: Keep deployment notes in your README

---

## 🎉 You're Done!

Your app is now:
- ✅ Live and accessible worldwide
- ✅ Deployed on professional platforms
- ✅ Auto-deploys on git push
- ✅ 100% free
- ✅ Ready to share with hiring managers!

**Your URLs:**
- Frontend: `https://your-app.vercel.app`
- Backend: `https://your-backend.onrender.com`

**Add these EVERYWHERE:**
- Resume
- LinkedIn
- Email signature
- GitHub profile
- Cover letters

---

**Next Steps:**
1. Deploy using steps above (25 minutes)
2. Test thoroughly
3. Update README with live link
4. Post on LinkedIn
5. Start applying to jobs with your live demo link!

Good luck! 🚀

