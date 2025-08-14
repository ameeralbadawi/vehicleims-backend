import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError

router = APIRouter()

CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET")
CLERK_API_KEY = os.getenv("CLERK_API_KEY")
CLERK_API_BASE = "https://api.clerk.com/v1"

@router.post("/clerk-webhook")
async def clerk_webhook(request: Request):
    # 1. Read raw payload
    payload = await request.body()
    print("Raw webhook payload:", payload.decode())

    # 2. Convert headers to dict for Svix verification
    headers = dict(request.headers)

    # 3. Verify the webhook signature
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        print(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    # 4. Extract event type and data
    event_type = event.get("type")
    data = event.get("data", {})
    print(f"Verified Clerk webhook event: {event_type}, data: {json.dumps(data)}")

    # 5. Only handle subscription events
    if event_type not in [
        "subscription.created",
        "subscription.updated",
        "subscription.active",
        "subscription.past_due",
    ]:
        print(f"Ignored event type: {event_type}")
        return {"status": "ignored"}

    clerk_user_id = data.get("user_id")
    subscription_status = data.get("status")  # e.g., "active", "past_due"

    if not clerk_user_id:
        raise HTTPException(status_code=400, detail="No user_id in subscription event")

    # 6. Update Clerk user's public_metadata
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{CLERK_API_BASE}/users/{clerk_user_id}",
            headers={
                "Authorization": f"Bearer {CLERK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"public_metadata": {"subscriptionStatus": subscription_status}},
        )

        if res.status_code >= 400:
            print(f"Failed to update user: {res.text}")
            raise HTTPException(status_code=res.status_code, detail=res.text)

    print(f"Updated user {clerk_user_id} subscription status to {subscription_status}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "new_status": subscription_status,
    }
