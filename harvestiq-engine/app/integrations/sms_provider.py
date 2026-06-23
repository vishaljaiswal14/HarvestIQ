from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class SmsProvider(ABC):
    @abstractmethod
    async def send_sms(self, to: str, body: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends an SMS message.
        """
        pass

class TwilioProvider(SmsProvider):
    def __init__(self) -> None:
        from app.integrations.twilio_client import TwilioClient
        self.client = TwilioClient()

    async def send_sms(self, to: str, body: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        return await self.client.send_sms(to, body, status_callback)

class Msg91Provider(SmsProvider):
    """
    Placeholder/design for Msg91 SMS Provider.
    For architectural expansion; not implemented in this phase.
    """
    def __init__(self, api_key: str = "", sender_id: str = "") -> None:
        self.api_key = api_key
        self.sender_id = sender_id

    async def send_sms(self, to: str, body: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "FAILED",
            "message_sid": None,
            "error": "Msg91Provider is designed but not implemented in this version"
        }

class ExotelProvider(SmsProvider):
    """
    Placeholder/design for Exotel SMS Provider.
    For architectural expansion; not implemented in this phase.
    """
    def __init__(self, sid: str = "", token: str = "", exophone: str = "") -> None:
        self.sid = sid
        self.token = token
        self.exophone = exophone

    async def send_sms(self, to: str, body: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "FAILED",
            "message_sid": None,
            "error": "ExotelProvider is designed but not implemented in this version"
        }
