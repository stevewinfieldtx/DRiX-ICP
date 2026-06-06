"""Stripe subscription webhooks (Section 12, step 6). Stub-safe if unconfigured."""
from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="")):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Billing not configured")
    import stripe

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    # TODO: map checkout.session.completed / customer.subscription.* to project tier.
    return {"received": True, "type": event.get("type")}
