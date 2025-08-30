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
        # Still return 200 even for signature errors to prevent webhook failures
        print(f"❌ Invalid signature: {e}")
        return {"status": "signature_error", "details": str(e)}

    event_type = event.get("type")
    data = event.get("data", {})
    
    print(f"✅ Verified event: {event_type}")
    print(json.dumps(data, indent=2))

    # Extract user_id from different event structures
    clerk_user_id = (
        data.get("id")  # user events
        or data.get("user_id")  # some subscription events
        or data.get("payer", {}).get("user_id")  # payment events
        or data.get("subscription", {}).get("user_id")  # subscription events
        or data.get("object", {}).get("user_id")  # subscription item events
    )
    
    if not clerk_user_id:
        print("❌ No user_id found in event data")
        # BUT STILL RETURN SUCCESS to avoid webhook failures
        return {"status": "success", "event": event_type, "reason": "no user_id"}

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

    elif event_type == "user.deleted":
        subscription_status = "inactive"
        subscription_plan = "None"

    # ----------------------
    # SUBSCRIPTION EVENTS
    # ----------------------
    elif event_type in [
        "subscription.created",
        "subscription.updated",
        "subscription.activated",
        "subscription.plan_changed",
    ]:
        # Check for active subscription items
        active_item = None
        subscription_data = data.get("subscription") or data
        
        # Look for active items in different possible locations
        items = (
            subscription_data.get("items", [])
            or subscription_data.get("subscription_items", [])
            or data.get("items", [])
        )
        
        active_item = next(
            (item for item in items if item.get("status") in ["active", "trialing"]),
            None,
        )
        
        if active_item:
            subscription_status = "active"
            subscription_plan = active_item.get("plan", {}).get("name", "None")
        else:
            # If no active items found, check subscription status directly
            if subscription_data.get("status") in ["active", "trialing"]:
                subscription_status = "active"
                subscription_plan = subscription_data.get("plan", {}).get("name", "None")

    elif event_type in [
        "subscription.past_due",
        "subscription.canceled",
        "subscription.expired",
        "subscriptionItem.ended",
        "subscriptionItem.canceled",
        "subscriptionItem.past_due",
        "subscriptionItem.incomplete"
    ]:
        subscription_status = "inactive"
        subscription_plan = "None"

    elif event_type in [
        "subscriptionItem.active",
        "subscriptionItem.created",
        "subscriptionItem.updated",
        "subscriptionItem.upcoming"
    ]:
        # These events indicate an active subscription
        subscription_status = "active"
        # Try to extract plan name from the item
        item_data = data.get("subscription_item") or data
        subscription_plan = item_data.get("plan", {}).get("name", "None")

    elif event_type == "subscriptionItem.abandoned":
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

            if res.status_code >= 400:
                print(f"❌ Failed to update Clerk: {res.status_code} - {res.text}")
                # BUT STILL RETURN SUCCESS to avoid webhook failures
                return {
                    "status": "success", 
                    "event": event_type, 
                    "warning": f"update failed: {res.text}",
                    "user_id": clerk_user_id
                }

            print(f"✅ Updated Clerk metadata for {clerk_user_id}: {metadata_update}")
            
        except Exception as e:
            print(f"❌ Exception during Clerk update: {e}")
            # STILL RETURN SUCCESS to avoid webhook failures
            return {
                "status": "success", 
                "event": event_type, 
                "warning": f"exception: {str(e)}",
                "user_id": clerk_user_id
            }

    else:
        print(f"ℹ️ No metadata update needed for event: {event_type}")

    # ALWAYS return success status
    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "metadata": metadata_update,
    }