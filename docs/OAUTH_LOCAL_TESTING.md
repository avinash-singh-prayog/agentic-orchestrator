# Google OAuth Local Testing Guide

## Issues Fixed

1. **Frontend Path Mismatch**: Fixed `/supervisor-agent` → `/supervisor-pinelabs` in `AuthScreen.tsx`
2. **Environment Variable**: Removed leading space from `OAUTH_REDIRECT_URI` in `.env`

## Prerequisites

1. Google OAuth credentials from [Google Cloud Console](https://console.cloud.google.com/)
2. Local development environment with Docker or Python

## Step 1: Configure Google OAuth Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Navigate to **APIs & Services** → **Credentials**
4. Create OAuth 2.0 Client ID (or use existing)
5. Add **Authorized redirect URIs**:
   - **Local**: `http://localhost:3044/supervisor-pinelabs/auth/google/callback`
   - **Production**: `https://prod-apis.prayog.io/supervisor-pinelabs/auth/google/callback`

## Step 2: Configure Local Environment

### Option A: Using Docker Compose (Recommended)

1. Update `Pinelabs.env` with your local values:

```bash
# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
FRONTEND_URL=http://localhost:3000
OAUTH_REDIRECT_URI=http://localhost:3044/supervisor-pinelabs/auth/google/callback
```

2. Start services:

```bash
docker-compose up supervisor-agent frontend
```

3. Access frontend at `http://localhost:3000`

### Option B: Running Supervisor Agent Directly

1. Navigate to supervisor agent directory:

```bash
cd src/orchestrator/supervisor_agent
```

2. Set environment variables:

```bash
export GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
export GOOGLE_CLIENT_SECRET=your-client-secret
export FRONTEND_URL=http://localhost:3000
export OAUTH_REDIRECT_URI=http://localhost:3044/supervisor-pinelabs/auth/google/callback
export DATABASE_URL=your-database-url
# ... other required env vars
```

3. Run the agent:

```bash
# Using uv (recommended)
uv run python -m app.main

# Or using Python directly
python -m app.main
```

4. The agent will start on `http://localhost:3044`

## Step 3: Test OAuth Flow

1. **Start the frontend** (if not using docker-compose):
   ```bash
   cd src/frontend
   npm install
   npm run dev
   ```

2. **Open browser** to `http://localhost:3000`

3. **Click "Google" login button**

4. **Expected flow**:
   - Redirects to Google OAuth consent screen
   - After authorization, redirects back to: `http://localhost:3044/supervisor-pinelabs/auth/google/callback?code=...`
   - Backend exchanges code for token
   - Redirects to frontend: `http://localhost:3000?token=<jwt-token>`
   - Frontend extracts token and logs user in

## Step 4: Verify Endpoints

Test the OAuth endpoints directly:

```bash
# Test login endpoint (should redirect to Google)
curl -I http://localhost:3044/supervisor-pinelabs/auth/google/login

# Test health endpoint
curl http://localhost:3044/supervisor-pinelabs/health
```

## Troubleshooting

### 503 Service Temporarily Unavailable

**Possible causes:**
1. **Wrong URL path**: Ensure using `/supervisor-pinelabs` not `/supervisor-agent`
2. **Service not running**: Check if supervisor-agent is running
3. **Database connection**: Verify `DATABASE_URL` is correct and accessible
4. **Environment variables**: Ensure all OAuth env vars are set correctly

**Debug steps:**
```bash
# Check supervisor agent logs
docker logs supervisor-agent

# Or if running directly, check console output
# Look for errors related to:
# - Database connection
# - Missing environment variables
# - OAuth configuration
```

### Redirect URI Mismatch

**Error**: `redirect_uri_mismatch`

**Solution**:
1. Ensure the redirect URI in Google Console **exactly matches** `OAUTH_REDIRECT_URI` in your `.env`
2. Check for:
   - Trailing slashes
   - HTTP vs HTTPS
   - Port numbers
   - Path case sensitivity

### Frontend Not Receiving Token

**Check**:
1. Browser console for errors
2. Network tab for redirect chain
3. Backend logs for OAuth errors
4. Ensure `FRONTEND_URL` matches your frontend URL

### Database Errors

**Common issues**:
- Connection timeout: Check `DATABASE_URL` and network connectivity
- Missing `google_id` column: Run migrations to add column to `users` table

**Check users table schema**:
```sql
-- Should have these columns:
-- id, email, password_hash, name, tenant_id, google_id
```

## Production Deployment Checklist

Before deploying to production:

- [ ] Update `OAUTH_REDIRECT_URI` to production URL
- [ ] Update `FRONTEND_URL` to production frontend URL
- [ ] Add production redirect URI in Google Console
- [ ] Ensure environment variables are set in deployment environment
- [ ] Test OAuth flow in production
- [ ] Verify HTTPS is used (required by Google OAuth)
- [ ] Check CORS settings if frontend and backend are on different domains

## Security Notes

1. **Never commit** `.env` files with real credentials
2. **Use environment variables** in production (not `.env` files)
3. **Rotate secrets** if accidentally exposed
4. **Use HTTPS** in production (Google OAuth requires it)
5. **Validate tokens** on backend before trusting them

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI OAuth Tutorial](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
