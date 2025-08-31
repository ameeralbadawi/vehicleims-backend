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
        print(f"❌ Invalid signature: {e}")
        return {"status": "signature_error", "details": str(e)}

    event_type = event.get("type")
    data = event.get("data", {})
    
    print(f"✅ Verified event: {event_type}")

    # Extract user_id - SIMPLIFIED and CORRECTED
    clerk_user_id = None
    
    # For user events: user_id is at data.id
    if event_type in ["user.created", "user.updated", "user.deleted"]:
        clerk_user_id = data.get("id")
        print(f"👤 User event - ID from data.id: {clerk_user_id}")
    
    # For subscription events: user_id is at data.payer.user_id
    elif "subscription" in event_type or "subscriptionItem" in event_type:
        clerk_user_id = data.get("payer", {}).get("user_id")
        print(f"💰 Subscription event - ID from data.payer.user_id: {clerk_user_id}")
    
    if not clerk_user_id:
        print("❌ No user_id found in event data")
        print(f"🔍 Available keys: {list(data.keys())}")
        return {"status": "success", "event": event_type, "reason": "no user_id"}

    print(f"👤 Final User ID: {clerk_user_id}")

    # Default values
    subscription_status = None
    subscription_plan = None
    metadata_update = {}

    # ----------------------
    # USER EVENTS
    # ----------------------
    if event_type == "user.created":
        print(f"🆕 New user created: {clerk_user_id}")
        subscription_status = "inactive"
        subscription_plan = "None"
        print(f"📝 Setting initial metadata: inactive, None")

    elif event_type == "user.deleted":
        print(f"🗑️ User deleted: {clerk_user_id}")
        subscription_status = "inactive"
        subscription_plan = "None"

    # ----------------------
    # SUBSCRIPTION ITEM EVENTS
    # ----------------------
    elif event_type in [
        "subscriptionItem.active",
        "subscriptionItem.created",
        "subscriptionItem.updated",
        "subscriptionItem.upcoming"
    ]:
        print(f"💰 Active subscription item event: {event_type}")
        subscription_status = "active"
        # Get plan name from the event data
        subscription_plan = data.get("plan", {}).get("name", "test")
        print(f"📋 Plan: {subscription_plan}")

    elif event_type in [
        "subscription.active",
        "subscription.created",
        "subscription.updated",
    ]:
        print(f"💰 Subscription event: {event_type}")
        subscription_data = data.get("subscription", data)
        status = subscription_data.get("status", "inactive")
        
        if status in ["active", "trialing"]:
            subscription_status = "active"
            subscription_plan = subscription_data.get("plan", {}).get("name", "test")
        else:
            subscription_status = "inactive"
            subscription_plan = "None"

    elif event_type in [
        "subscriptionItem.ended",
        "subscriptionItem.canceled",
        "subscriptionItem.past_due",
        "subscriptionItem.incomplete",
        "subscriptionItem.abandoned",
        "subscription.past_due",
        "subscription.canceled",
        "subscription.expired"
    ]:
        print(f"🔴 Inactive event: {event_type}")
        subscription_status = "inactive"
        subscription_plan = "None"

    # ----------------------
    # APPLY UPDATE
    # ----------------------
    if subscription_status is not None:
        metadata_update["subscriptionStatus"] = subscription_status
        metadata_update["subscriptionPlan"] = subscription_plan

        print(f"🔄 Updating metadata: {metadata_update}")

        try:
            async with httpx.AsyncClient() as client:
                res = await client.patch(
                    f"{CLERK_API_BASE}/users/{clerk_user_id}/metadata",
                    headers={
                        "Authorization": f"Bearer {CLERK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"public_metadata": metadata_update},
                )

            if res.status_code == 200:
                print(f"✅ Successfully updated metadata for {clerk_user_id}")
                print(f"📋 New metadata: {metadata_update}")
            else:
                print(f"❌ Failed to update Clerk: {res.status_code} - {res.text}")
                print(f"💥 This might be why metadata isn't updating!")
                
        except Exception as e:
            print(f"❌ Exception during Clerk update: {e}")

    else:
        print(f"ℹ️ No metadata update needed for event: {event_type}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "metadata": metadata_update,
    }