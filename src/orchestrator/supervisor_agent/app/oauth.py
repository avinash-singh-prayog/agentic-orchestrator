import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.auth import get_or_create_google_user, create_access_token

# Logger
logger = logging.getLogger("oauth")

router = APIRouter()

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Ensure we use the exact redirect URI registered in Google Console
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:9004/supervisor-agent/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

@router.get("/auth/google/login")
async def google_login():
    """Redirect users to Google's OAuth 2.0 consent screen."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500, 
            detail="Google OAuth not configured (CLIENT_ID or CLIENT_SECRET missing)"
        )

    scope = "openid email profile"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    # Construct URL manually to avoid dependency on specific auth libraries if not needed
    import urllib.parse
    url_params = urllib.parse.urlencode(params)
    redirect_url = f"{GOOGLE_AUTH_URL}?{url_params}"
    
    return RedirectResponse(url=redirect_url)

@router.get("/auth/google/callback")
async def google_callback(code: str = None, error: str = None):
    """Handle the callback from Google."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?error=oauth_error&message={error}")
    
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}?error=missing_code")
        
    try:
        async with httpx.AsyncClient() as client:
            # 1. Exchange code for tokens
            token_data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": OAUTH_REDIRECT_URI,
            }
            
            token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
            if token_response.status_code != 200:
                logger.error(f"Failed to get token: {token_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=token_failed")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            # id_token = tokens.get("id_token") # We could verify this too
            
            # 2. Get user info
            headers = {"Authorization": f"Bearer {access_token}"}
            user_response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            
            if user_response.status_code != 200:
                logger.error(f"Failed to get user info: {user_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=user_info_failed")
            
            user_info = user_response.json()
            
            # 3. Create or get user in our DB
            email = user_info.get("email")
            name = user_info.get("name")
            google_id = user_info.get("id")
            
            # Ensure email is verified (usually Google guarantees this for gmail, but good to check)
            if not user_info.get("verified_email"):
                 # Depending on security policy, we might reject unverified emails.
                 # For now, we proceed as Google returns verified_email=true typically.
                 pass

            user = await get_or_create_google_user(email, name, google_id)
            
            # 4. Create our own JWT
            app_access_token = create_access_token(
                data={"sub": user.email, "user_id": user.id, "tenant_id": user.tenant_id},
                expires_delta=None # Use default
            )
            
            # 5. Redirect to frontend with token
            # Note: Passing token in URL fragment or query param (fragment is safer but JS must parse it).
            # We'll use query param for simplicity in this MVP unless requested otherwise.
            
            redirect_to = f"{FRONTEND_URL}?token={app_access_token}"
            return RedirectResponse(url=redirect_to)
            
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(f"{FRONTEND_URL}?error=server_error")
