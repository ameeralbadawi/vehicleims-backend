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
    
    print(f"✅ Received event: {event_type}")

    # Extract user_id from payer object
    clerk_user_id = data.get("payer", {}).get("user_id")
    
    if not clerk_user_id:
        print("ℹ️ No user_id found - skipping")
        return {"status": "success", "event": event_type, "reason": "no user_id"}

    print(f"👤 User ID: {clerk_user_id}")

    # Only process PAID subscription events
    subscription_status = None
    subscription_plan = None

    # Check for PAID subscription items
    if event_type in [
        "subscriptionItem.active",
        "subscriptionItem.created", 
        "subscriptionItem.updated",
        "subscription.active",
        "subscription.created",
        "subscription.updated"
    ]:
        print(f"💰 Processing subscription event: {event_type}")
        
        # Get all items from the event
        items = []
        if "items" in data:
            items = data["items"]
        elif "subscription_item" in data:
            items = [data]
        elif event_type.startswith("subscriptionItem"):
            items = [data]
        
        # Look for ANY paid subscription item
        for item in items:
            plan = item.get("plan", {})
            amount = plan.get("amount", 0)
            plan_name = plan.get("name", "").lower()
            status = item.get("status", "")
            
            print(f"📋 Item: {plan_name}, Amount: {amount}, Status: {status}")
            
            # Only process ACTIVE paid items (amount > 0)
            if amount > 0 and status == "active" and plan_name not in ["free", "none"]:
                subscription_status = "active"
                subscription_plan = plan.get("name", "paid")
                print(f"✅ PAID ACTIVE ITEM FOUND: {plan_name} (${amount})")
                break

    # Apply the update ONLY if we found a paid active subscription
    if subscription_status == "active":
        metadata_update = {
            "subscriptionStatus": subscription_status,
            "subscriptionPlan": subscription_plan
        }

        print(f"🔄 Setting PAID subscription: {metadata_update}")

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
                print(f"✅ Successfully set PAID subscription metadata!")
            else:
                print(f"❌ Failed to update Clerk: {res.status_code}")
                print(f"💥 Response: {res.text}")
                
        except Exception as e:
            print(f"❌ Exception during update: {e}")

    else:
        print(f"ℹ️ No PAID active subscription found in {event_type} - skipping update")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "updated": subscription_status == "active"
    }