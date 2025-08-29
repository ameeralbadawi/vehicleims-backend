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
    payload = await request.body()
    headers = dict(request.headers)

    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    event_type = event.get("type")
    data = event.get("data", {})

    print(f"✅ Verified event: {event_type}")
    print(json.dumps(data, indent=2))

    # figure out user_id depending on event type
    clerk_user_id = data.get("id") or data.get("user_id") or data.get("payer", {}).get("user_id")
    if not clerk_user_id:
        return {"status": "skipped", "reason": "no user_id"}

    # default values
    subscription_status = None
    subscription_plan = None
    metadata_update = {}

    # ----------------------
    # USER EVENTS
    # ----------------------
    if event_type == "user.created":
        subscription_status = "inactive"
        subscription_plan = "None"

    elif event_type == "user.deleted":
        # Wipe subscription info when user deleted
        subscription_status = "inactive"
        subscription_plan = "None"

    elif event_type == "user.updated":
        # usually you don’t need to touch metadata here unless you want to
        pass

    # ----------------------
    # SUBSCRIPTION EVENTS
    # ----------------------
    elif event_type in [
        "subscription.created",
        "subscription.updated",
        "subscription.activated",
        "subscription.plan_changed",
    ]:
        active_item = next(
            (item for item in data.get("items", []) if item.get("status") == "active"),
            None,
        )
        if active_item:
            subscription_status = "active"
            subscription_plan = active_item.get("plan", {}).get("name", "None")

    elif event_type in [
        "subscription.past_due",
        "subscription.canceled",
        "subscription.expired",
    ]:
        subscription_status = "inactive"
        subscription_plan = "None"

    # ----------------------
    # APPLY UPDATE IF NEEDED
    # ----------------------
    if subscription_status is not None or subscription_plan is not None:
        if subscription_status is not None:
            metadata_update["subscriptionStatus"] = subscription_status
        if subscription_plan is not None:
            metadata_update["subscriptionPlan"] = subscription_plan

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
            print(f"❌ Failed to update Clerk: {res.text}")
            return {"status": "error", "details": res.text}

        print(f"✅ Updated Clerk metadata for {clerk_user_id}: {metadata_update}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "metadata": metadata_update,
    }
