import logging
from typing import Optional
import httpx
from app.core.config import get_settings
from app.core.twilio_security import is_local_callback_url

logger = logging.getLogger(__name__)

def map_twilio_error(provider_status: str, error_code: Optional[str] = None, error_message: Optional[str] = None) -> tuple[str, str]:
    status_upper = provider_status.upper()
    if status_upper in ["FAILED", "UNDELIVERED"]:
        mapped_status = "FAILED"
    elif status_upper == "DELIVERED":
        mapped_status = "DELIVERED"
    elif status_upper == "SENT":
        mapped_status = "SENT"
    else:
        mapped_status = "QUEUED"
        
    friendly_err = ""
    if mapped_status == "FAILED":
        code_str = str(error_code) if error_code is not None else ""
        msg_str = (error_message or "").lower()
        
        if code_str == "21608" or "unverified" in msg_str:
            friendly_err = "Number not verified on Twilio trial account"
        elif code_str == "21211" or "invalid" in msg_str:
            friendly_err = "Invalid phone number"
        elif code_str in ["30044", "63038"] or "trial" in msg_str or "limit" in msg_str:
            friendly_err = "Trial account restriction"
        elif (code_str.startswith("300") or "carrier" in msg_str) and code_str != "30044":
            friendly_err = "Carrier delivery failed"
        else:
            friendly_err = "Provider delivery failed"
            
    return mapped_status, friendly_err


class TwilioClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_sms(self, to: str, body: str, status_callback: Optional[str] = None) -> dict:
        """
        Sends an SMS via Twilio.
        If Twilio credentials are not set, it returns a mock success response.
        Returns:
            dict: {
                "status": "QUEUED" | "SENT" | "FAILED",
                "message_sid": str | None,
                "provider_status": str | None,
                "error_code": str | None,
                "error_message": str | None,
                "error": str | None
            }
        """
        if not self.settings.twilio_enabled:
            # When disabled (dev/demo mode), return a mock success delivery
            return {
                "status": "QUEUED",
                "message_sid": "mock_twilio_sid_" + str(to[-4:]),
                "provider_status": "queued",
                "error_code": None,
                "error_message": None,
                "error": None
            }

        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.settings.twilio_account_sid}/Messages.json"
        )
        data = {
            "To": to,
            "From": self.settings.twilio_from_number,
            "Body": body[:1600],
        }
        if status_callback:
            is_local = is_local_callback_url(status_callback)
            if not is_local:
                data["StatusCallback"] = status_callback
        logger.info("Sending Twilio SMS to=%s body_length=%s callback_configured=%s", to, len(body), bool(status_callback))

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
                    data=data,
                )
                logger.info("Twilio API responded with status_code=%s", response.status_code)
                if response.status_code in (200, 201):
                    res_data = response.json()
                    status_raw = res_data.get("status", "queued").upper()
                    mapped_status = "SENT" if status_raw == "SENT" else "QUEUED"
                    ret = {
                        "status": mapped_status,
                        "message_sid": res_data.get("sid"),
                        "provider_status": res_data.get("status"),
                        "error_code": None,
                        "error_message": None,
                        "error": None
                    }
                    logger.info("Twilio SMS queued successfully sid=%s", res_data.get("sid"))
                    return ret
                else:
                    logger.warning("Twilio API rejected SMS with status_code=%s", response.status_code)
                    err_code = None
                    err_msg = ""
                    try:
                        res_data = response.json()
                        err_code = res_data.get("code")
                        err_msg = res_data.get("message", "")
                    except Exception:
                        err_msg = response.text
                    
                    _, friendly_err = map_twilio_error("FAILED", err_code, err_msg)
                    ret = {
                        "status": "FAILED",
                        "message_sid": None,
                        "provider_status": "failed",
                        "error_code": str(err_code) if err_code else None,
                        "error_message": friendly_err or "Provider rejected",
                        "error": friendly_err or "Provider rejected"
                    }
                    logger.warning("Twilio SMS failed code=%s message=%s", ret["error_code"], ret["error_message"])
                    return ret
        except Exception as exc:
            logger.exception("Exception during Twilio SMS send")
            return {
                "status": "FAILED",
                "message_sid": None,
                "provider_status": "failed",
                "error_code": None,
                "error_message": f"Exception sending SMS: {str(exc)}",
                "error": f"Exception sending SMS: {str(exc)}"
            }
