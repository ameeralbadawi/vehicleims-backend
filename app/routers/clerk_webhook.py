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
    
    print(f"🔔 Received event: {event_type}")
    print(f"📦 Event data: {json.dumps(data, indent=2)}")

    # Extract user_id from different event structures
    clerk_user_id = None
    
    # Try different paths to find user_id
    possible_user_id_paths = [
        data.get("id"),
        data.get("user_id"),
        data.get("payer", {}).get("user_id"),
        data.get("subscription", {}).get("user_id"),
        data.get("object", {}).get("user_id"),
        data.get("subscription_item", {}).get("subscription", {}).get("user_id"),
        data.get("items", [{}])[0].get("subscription", {}).get("user_id") if data.get("items") else None
    ]
    
    for user_id in possible_user_id_paths:
        if user_id:
            clerk_user_id = user_id
            break
    
    if not clerk_user_id:
        print("❌ No user_id found in event data. Available keys:", list(data.keys()))
        if "subscription" in data:
            print("📋 Subscription data:", data["subscription"])
        if "subscription_item" in data:
            print("📋 Subscription item data:", data["subscription_item"])
        return {"status": "skipped", "reason": "no user_id"}

    print(f"👤 User ID extracted: {clerk_user_id}")

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
    # SUBSCRIPTION EVENTS - CRITICAL SECTION
    # ----------------------
    elif event_type in [
        "subscription.created",
        "subscription.updated",
        "subscription.activated",
        "subscription.plan_changed",
        "subscriptionItem.active",
        "subscriptionItem.created",
        "subscriptionItem.updated"
    ]:
        print(f"💰 Subscription event: {event_type}")
        
        # Try to get subscription data from different locations
        subscription_data = (
            data.get("subscription") 
            or data.get("subscription_item", {}).get("subscription")
            or data
        )
        
        print(f"📊 Subscription data: {json.dumps(subscription_data, indent=2)}")
        
        # Check subscription status
        sub_status = subscription_data.get("status")
        print(f"📈 Subscription status: {sub_status}")
        
        if sub_status in ["active", "trialing"]:
            subscription_status = "active"
            
            # Try to get plan name from different locations
            subscription_plan = (
                subscription_data.get("plan", {}).get("name")
                or subscription_data.get("plan_name")
                or subscription_data.get("items", [{}])[0].get("plan", {}).get("name")
                or "Unknown Plan"
            )
            print(f"📋 Subscription plan: {subscription_plan}")
        else:
            subscription_status = "inactive"
            subscription_plan = "None"

    elif event_type in [
        "subscription.past_due",
        "subscription.canceled",
        "subscription.expired",
        "subscriptionItem.ended",
        "subscriptionItem.canceled",
        "subscriptionItem.past_due",
        "subscriptionItem.incomplete",
        "subscriptionItem.abandoned"
    ]:
        print(f"🔴 Inactive subscription event: {event_type}")
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

        print(f"🔄 Attempting to update metadata for {clerk_user_id}: {metadata_update}")

        try:
            async with httpx.AsyncClient() as client:
                # Use the correct endpoint for updating metadata
                res = await client.patch(
                    f"{CLERK_API_BASE}/users/{clerk_user_id}/metadata",
                    headers={
                        "Authorization": f"Bearer {CLERK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"public_metadata": metadata_update},
                )

            if res.status_code == 200:
                print(f"✅ Successfully updated Clerk metadata for {clerk_user_id}")
                print(f"📋 New metadata: {metadata_update}")
            else:
                print(f"❌ Failed to update Clerk: {res.status_code} - {res.text}")
                return {"status": "error", "details": res.text}
            
        except Exception as e:
            print(f"❌ Exception during Clerk update: {e}")
            return {"status": "error", "details": str(e)}

    else:
        print(f"ℹ️ No metadata update needed for event: {event_type}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "metadata": metadata_update,
    }