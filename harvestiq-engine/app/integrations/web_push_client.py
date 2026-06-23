import json
from typing import Any, Optional

from app.core.config import get_settings


class WebPushClient:
    """Web Push delivery via VAPID. Mocks success when keys are not configured."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.vapid_public_key and self.settings.vapid_private_key)

    def get_public_key(self) -> str:
        return self.settings.vapid_public_key

    async def send_notification(
        self,
        subscription: dict[str, Any],
        title: str,
        body: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = json.dumps({"title": title, "body": body, "data": data or {}})

        if not self.enabled:
            return {
                "status": "DELIVERED",
                "error": None,
                "mock": True,
            }

        try:
            from pywebpush import WebPushException, webpush

            webpush(
                subscription_info={
                    "endpoint": subscription["endpoint"],
                    "keys": subscription["keys"],
                },
                data=payload,
                vapid_private_key=self.settings.vapid_private_key,
                vapid_claims={"sub": self.settings.vapid_subject},
            )
            return {"status": "DELIVERED", "error": None, "mock": False}
        except WebPushException as exc:
            return {
                "status": "FAILED",
                "error": str(exc),
                "mock": False,
            }
        except Exception as exc:
            return {
                "status": "FAILED",
                "error": f"Push delivery error: {exc}",
                "mock": False,
            }
