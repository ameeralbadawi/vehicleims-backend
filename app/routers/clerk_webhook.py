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
    print("\n--- Clerk Webhook Received ---")
    print(payload.decode())

    # 2. Convert headers for Svix verification
    headers = dict(request.headers)

    # 3. Verify webhook signature
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        print(f"❌ Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    # 4. Extract event details
    event_type = event.get("type")
    data = event.get("data", {})
    print(f"✅ Verified event: {event_type}")
    print(json.dumps(data, indent=2))

    # 5. Only handle subscription-related events
    if not event_type.startswith("subscription."):
        print(f"ℹ Ignored event type: {event_type}")
        return {"status": "ignored"}

    # 6. Get the correct user_id
    clerk_user_id = data.get("user_id") or data.get("payer", {}).get("user_id")
    if not clerk_user_id:
        print("⚠ No user_id found in event, skipping update.")
        return {"status": "skipped", "reason": "no user_id"}

    # 7. Determine subscription status & plan
    active_item = next(
        (item for item in data.get("items", []) if item.get("status") == "active"),
        None
    )

    if active_item:
        subscription_status = active_item.get("status", "unknown")
        subscription_plan = active_item.get("plan", {}).get("name", "Free")
    else:
        subscription_status = "inactive"
        subscription_plan = "Free"

    print(f"📦 User {clerk_user_id} plan: {subscription_plan}, status: {subscription_status}")

    # 8. Update Clerk user's public_metadata
    metadata_update = {
        "subscriptionStatus": subscription_status,
        "subscriptionPlan": subscription_plan
    }

    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{CLERK_API_BASE}/users/{clerk_user_id}",
            headers={
                "Authorization": f"Bearer {CLERK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"public_metadata": metadata_update},
        )

    if res.status_code >= 400:
        print(f"❌ Failed to update user in Clerk: {res.text}")
        return {"status": "error", "details": res.text}

    print(f"✅ Updated Clerk public_metadata for {clerk_user_id}: {metadata_update}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "new_status": subscription_status,
        "plan": subscription_plan
    }
