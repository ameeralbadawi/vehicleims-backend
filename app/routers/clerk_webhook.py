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
    print(f"📦 Full event data: {json.dumps(data, indent=2)}")

    # Extract user_id
    clerk_user_id = None
    
    # For subscription events, the user_id is usually in the subscription object
    if "subscription" in data:
        clerk_user_id = data["subscription"].get("user_id")
    elif data.get("object") == "subscription":
        clerk_user_id = data.get("user_id")
    
    # Fallback to other locations
    if not clerk_user_id:
        clerk_user_id = (
            data.get("id")  # user events
            or data.get("user_id")  # some events
            or data.get("payer", {}).get("user_id")  # payment events
        )
    
    if not clerk_user_id:
        print("❌ No user_id found in event data")
        return {"status": "success", "event": event_type, "reason": "no user_id"}

    print(f"👤 User ID: {clerk_user_id}")

    # Default values
    subscription_status = None
    subscription_plan = None
    metadata_update = {}

    # ----------------------
    # USER EVENTS
    # ----------------------
    if event_type == "user.created":
        subscription_status = "inactive"
        subscription_plan = "None"
        print(f"🆕 New user created: {clerk_user_id}")

    elif event_type == "user.deleted":
        subscription_status = "inactive"
        subscription_plan = "None"
        print(f"🗑️ User deleted: {clerk_user_id}")

    # ----------------------
    # SUBSCRIPTION EVENTS - CORRECTED EVENT TYPES
    # ----------------------
    elif event_type in [
        "subscription.active",  # CORRECTED: was "subscription.activated"
        "subscription.created",
        "subscription.updated",
        "subscription.plan_changed",
    ]:
        print(f"💰 Subscription event: {event_type}")
        
        # Get subscription data
        subscription_data = data.get("subscription", data)
        print(f"📊 Subscription data: {json.dumps(subscription_data, indent=2)}")
        
        # Check status
        status = subscription_data.get("status")
        print(f"📈 Subscription status: {status}")
        
        if status in ["active", "trialing"]:
            subscription_status = "active"
            subscription_plan = "test"  # Your plan name
            print(f"✅ Active subscription: {subscription_plan}")
        else:
            subscription_status = "inactive"
            subscription_plan = "None"
            print(f"❌ Inactive subscription: {status}")

    elif event_type in [
        "subscription.past_due",
        "subscription.canceled",
        "subscription.expired",
    ]:
        print(f"🔴 Inactive subscription event: {event_type}")
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
        print(f"🟢 Active subscription item event: {event_type}")
        subscription_status = "active"
        subscription_plan = "test"  # Your plan name

    elif event_type in [
        "subscriptionItem.ended",
        "subscriptionItem.canceled",
        "subscriptionItem.past_due",
        "subscriptionItem.incomplete",
        "subscriptionItem.abandoned"
    ]:
        print(f"🔴 Inactive subscription item event: {event_type}")
        subscription_status = "inactive"
        subscription_plan = "None"

    # ----------------------
    # APPLY UPDATE IF NEEDED
    # ----------------------
    if subscription_status is not None:
        metadata_update["subscriptionStatus"] = subscription_status
        metadata_update["subscriptionPlan"] = subscription_plan

        print(f"🔄 Attempting to update metadata: {metadata_update}")

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
                
        except Exception as e:
            print(f"❌ Exception during Clerk update: {e}")

    else:
        print(f"ℹ️ No metadata update needed for event: {event_type}")

    # ALWAYS return success status
    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "metadata": metadata_update,
    }