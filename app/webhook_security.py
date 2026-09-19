from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, status

from app.config import Settings


def verify_webhook(
    provider: str,
    body: bytes,
    signature_header: str | None,
    settings: Settings,
) -> str:
    """Verify SlotBridge HMAC ingress or explicitly allow development demo traffic.

    This is an extension point, not a claim that vendors use this exact header.
    Provider-native verifiers can replace the HMAC policy once their documented
    webhook contracts and credentials are available.
    """
    secret_setting = {
        "mindbody": settings.mindbody_webhook_secret,
        "vagaro": settings.vagaro_webhook_secret,
        "google": settings.google_webhook_secret,
    }.get(provider)

    if secret_setting is not None:
        if not signature_header or not signature_header.startswith("sha256="):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )
        expected = hmac.new(
            secret_setting.get_secret_value().encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        supplied = signature_header.removeprefix("sha256=").strip().lower()
        if not hmac.compare_digest(expected, supplied):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
        return "slotbridge-hmac-sha256"

    if (
        settings.allow_unsigned_demo_webhooks
        and settings.slotbridge_environment in {"development", "test", "demo"}
    ):
        return "unsigned-demo"

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Webhook verification is not configured for this provider",
    )
