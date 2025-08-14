import os
import json
import logging
import httpx
from fastapi import APIRouter, Request
from svix.webhooks import Webhook, WebhookVerificationError

router = APIRouter()

CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET")
CLERK_API_KEY = os.getenv("CLERK_API_KEY")
CLERK_API_BASE = "https://api.clerk.com/v1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/clerk-webhook")
async def clerk_webhook(request: Request):
    payload = await request.body()
    logger.info(f"Raw webhook payload: {payload.decode()}")

    headers = dict(request.headers)

    # Verify signature, but don’t fail if invalid
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
        logger.info("Webhook signature verified")
    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        event = {}  # continue processing

    event_type = event.get("type", "unknown")
    data = event.get("data", {})
    logger.info(f"Webhook event: {event_type}, data: {json.dumps(data)}")

    # Get user_id and subscription info
    clerk_user_id = data.get("user_id")
    subscription_status = data.get("status", "unknown")
    plan_name = data.get("plan_name", "Free")  # default to Free if not provided

    # Update Clerk user if we have a user_id
    if clerk_user_id:
        metadata_update = {
            "subscriptionStatus": subscription_status,
            "subscriptionPlan": plan_name
        }
        try:
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
                    logger.error(f"Failed to update user {clerk_user_id}: {res.text}")
                else:
                    logger.info(f"Updated user {clerk_user_id} metadata: {metadata_update}")
        except Exception as e:
            logger.error(f"Error updating user {clerk_user_id}: {e}")
    else:
        logger.warning("No user_id found in event, skipping update")

    # Always return 200 to prevent webhook retries
    return {
        "status": "received",
        "event_type": event_type,
        "user_id": clerk_user_id,
        "subscription_status": subscription_status,
        "plan_name": plan_name
    }
