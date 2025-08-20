# auth.py - HEAVILY DEBUGGED VERSION
import os
from fastapi import HTTPException, Header
import jwt
from jwt import PyJWKClient
import json

# JWT configuration
CLERK_JWKS_URL = "https://fit-giraffe-55.clerk.accounts.dev/.well-known/jwks.json"
jwks_client = PyJWKClient(CLERK_JWKS_URL)

async def get_authenticated_user(authorization: str = Header(None)):
    print("=== AUTH DEBUG START ===")
    
    if not authorization:
        print("❌ No authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        print("❌ Invalid authorization format")
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "").strip()
    print(f"Token received: {token[:50]}...")

    try:
        # Debug: Print the token payload without verification
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            print(f"Unverified payload: {json.dumps(unverified_payload, indent=2)}")
        except:
            print("Could not decode unverified payload")

        # Get the signing key
        print("🔑 Getting signing key...")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        print(f"Signing key found: {signing_key.key_id}")

        # Verify JWT token
        print("🔐 Verifying JWT...")
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="backend-api",  # MUST match your template name
            issuer="https://fit-giraffe-55.clerk.accounts.dev",
            options={"verify_exp": True}
        )
        
        print(f"✅ JWT verified successfully!")
        print(f"User ID: {payload.get('user_id')}")
        print("=== AUTH DEBUG END ===")
        return payload.get("user_id")
            
    except jwt.ExpiredSignatureError:
        print("❌ Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError as e:
        print(f"❌ Invalid audience error: {e}")
        print(f"Expected audience: 'backend-api'")
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidIssuerError as e:
        print(f"❌ Invalid issuer error: {e}")
        print(f"Expected issuer: 'https://fit-giraffe-55.clerk.accounts.dev'")
        raise HTTPException(status_code=401, detail="Invalid issuer")
    except Exception as e:
        print(f"❌ JWT verification failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("=== AUTH DEBUG END ===")
        raise HTTPException(status_code=401, detail="Invalid token")