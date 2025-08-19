# auth.py
import os
from fastapi import HTTPException, Header
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=os.getenv("CLERK_API_KEY"))

async def get_authenticated_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        result = await clerk.sessions.authenticate_request(
            headers={"authorization": f"Bearer {token}"}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    if not result or not result.is_signed_in:
        raise HTTPException(status_code=401, detail="Not signed in")

    return result.user_id
