# auth.py
import os
from fastapi import HTTPException, Header
from clerk_backend_api import Clerk

# Initialize Clerk client with your backend API key
clerk = Clerk(bearer_auth=os.getenv("CLERK_API_KEY"))

async def get_authenticated_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()

    try:
        # Verify the frontend session JWT using Clerk
        session = await clerk.sessions.verify_session(token)
    except Exception as e:
        print(f"Session verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    if not session or not session.user_id:
        raise HTTPException(status_code=401, detail="Not signed in")

    # Return the user ID so downstream endpoints know who is authenticated
    return session.user_id
