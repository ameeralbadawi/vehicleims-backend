# auth.py - UPDATED FOR JWT TEMPLATES
import os
from fastapi import HTTPException, Header
import jwt
from jwt import PyJWKClient

# JWT configuration
CLERK_JWKS_URL = "https://fit-giraffe-55.clerk.accounts.dev/.well-known/jwks.json"
jwks_client = PyJWKClient(CLERK_JWKS_URL)

async def get_authenticated_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "").strip()

    try:
        # Verify JWT token
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="backend-api",  # MUST match your template name exactly
            issuer="https://fit-giraffe-55.clerk.accounts.dev",  # Your Clerk instance
            options={"verify_exp": True}
        )
        
        print(f"✅ JWT verified for user: {payload.get('user_id')}")
        return payload.get("user_id")
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid issuer")
    except Exception as e:
        print(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")