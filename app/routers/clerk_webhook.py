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

    # Process subscription events
    subscription_status = None
    subscription_plan = None

    if event_type in [
        "subscriptionItem.active",
        "subscriptionItem.created", 
        "subscriptionItem.updated",
        "subscription.active",
        "subscription.created",
        "subscription.updated"
    ]:
        print(f"💰 Processing subscription event: {event_type}")
        
        # Check for PAID subscription items
        items = data.get("items", [])
        if not items and "subscription_item" in data:
            # Handle single subscription item events
            items = [data]
        
        # Look for any PAID subscription items
        paid_item_found = False
        for item in items:
            plan = item.get("plan", {})
            amount = plan.get("amount", 0)
            plan_name = plan.get("name", "").lower()
            
            print(f"📋 Item: {plan_name}, Amount: {amount}")
            
            # If we find ANY paid item, the user should be active
            if amount > 0 and plan_name not in ["free", "none"]:
                paid_item_found = True
                subscription_status = "active"
                subscription_plan = plan.get("name", "paid")
                print(f"✅ Paid item found: {plan_name} (${amount})")
                break
        
        if paid_item_found:
            print(f"🎯 Setting user to ACTIVE with plan: {subscription_plan}")
        else:
            # No paid items found, check if this is a free plan
            subscription_status = "inactive"
            subscription_plan = "None"
            print(f"🔓 No paid items found - setting to INACTIVE")

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
        print(f"🔴 Cancellation event: {event_type}")
        subscription_status = "inactive"
        subscription_plan = "None"

    # Apply the update
    if subscription_status is not None:
        metadata_update = {
            "subscriptionStatus": subscription_status,
            "subscriptionPlan": subscription_plan
        }

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
                print(f"✅ Successfully updated metadata!")
            else:
                print(f"❌ Failed to update Clerk: {res.status_code}")
                print(f"💥 Response: {res.text}")
                
        except Exception as e:
            print(f"❌ Exception during update: {e}")

    else:
        print(f"ℹ️ No subscription status change needed for {event_type}")

    return {
        "status": "success",
        "event": event_type,
        "user_id": clerk_user_id,
        "updated": subscription_status is not None
    }