# 📧 Email Setup Guide

Quick guide to get email verification working in 5 minutes.

## 1. Get SendGrid API Key (Free)

### Sign Up
1. Go to https://signup.sendgrid.com/
2. Create free account (100 emails/day forever)
3. Verify your account

### Create API Key
1. Go to **Settings** → **API Keys**
2. Click **Create API Key**
3. Name: `AI_Document_Search`
4. Permissions: **Mail Send** (or Full Access)
5. **Copy the key** (you only see it once!)

### Verify Sender
1. Go to **Settings** → **Sender Authentication**
2. **Verify a Single Sender**
3. Enter your email (can be Gmail, etc.)
4. Check your email and click verify link

## 2. Configure Backend

Edit `backend/.env` (create if doesn't exist):

```ini
# Email Settings
SENDGRID_API_KEY=SG.your_api_key_here
FROM_EMAIL=your-verified-email@gmail.com
FROM_NAME=AI Document Search
FRONTEND_URL=http://localhost:3000
```

**Important:** Use the same email you verified in SendGrid for `FROM_EMAIL`.

## 3. Restart Backend

```powershell
# Stop backend (Ctrl+C)
# Start again:
cd backend
python main.py
```

## 4. Test It!

1. Sign up with a **real email** (your own)
2. Check your inbox for verification email
3. Click the verification link
4. Done! ✅

## Testing Password Reset

1. Click **"Forgot password?"** on login page
2. Enter your email
3. Check inbox for reset link
4. Click link and set new password
5. Log in with new password

---

## Troubleshooting

### "No emails arriving"

**Check backend logs:**
```
INFO: Email sent successfully: Verify your email address to user@example.com
```

If you see:
```
WARNING: Email service disabled - no valid SENDGRID_API_KEY found
```

→ Check your `.env` file has the correct API key

### "Email in spam folder"

Normal for free SendGrid accounts. To fix:
- Verify your domain (not just email) in SendGrid
- Use a real domain email (not Gmail)
- Warm up your sender reputation

### "Verification link doesn't work"

Check `FRONTEND_URL` in `.env`:
- Development: `http://localhost:3000`
- Production: `https://yourdomain.com`

---

## Without SendGrid (Development Only)

You can develop without email by:

1. Leave `SENDGRID_API_KEY` empty in `.env`
2. Check backend logs for tokens:
   ```
   WARNING: Email sending skipped (disabled): Verify your email...
   ```
3. Manually verify users in `backend/data/users.json`:
   ```json
   {
     "username": {
       "email_verified": true  ← Change to true
     }
   }
   ```

**Note:** This is only for development. Use SendGrid in production!

---

## Cost

**Free Tier:**
- 100 emails/day
- Perfect for development and small apps
- No credit card required
- No expiration

**Upgrade if you need:**
- More than 100 emails/day
- Better deliverability
- Custom domain
- Detailed analytics

---

## Alternative Email Providers

If you don't want to use SendGrid:

**AWS SES:**
- Cheaper at scale
- Requires AWS account
- More complex setup

**Mailgun:**
- Similar to SendGrid
- 100 free emails/day

**Postmark:**
- Great deliverability
- More expensive

**Resend:**
- Modern API
- 100 free emails/day

To switch providers, edit `backend/services/email_service.py`.

---

## Quick Reference

### Environment Variables
```ini
SENDGRID_API_KEY=SG.xxx
FROM_EMAIL=noreply@yourdomain.com
FROM_NAME=AI Document Search
FRONTEND_URL=http://localhost:3000
```

### Test Command
```powershell
python -m pytest tests/test_email.py -v
```

### Check Email Service Status
```powershell
cd backend
python -c "from services.email_service import get_email_service; s = get_email_service(); print('Enabled:', s.enabled)"
```

---

**That's it! Email verification is now working.** 🎉

Questions? Check `DAY_3-4_COMPLETE.md` for full documentation.

