import os
import httpx
from fastapi import HTTPException, Header

CLERK_API_KEY = os.getenv("CLERK_API_KEY")

async def get_authenticated_user(authorization: str = Header(None)):
    """
    Verifies the Clerk session token and returns the user's ID.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.clerk.dev/v1/sessions/verify",
            headers={
                "Authorization": f"Bearer {CLERK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"token": token}
        )

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    session_data = res.json()
    user_id = session_data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID found in session")

    return user_id
