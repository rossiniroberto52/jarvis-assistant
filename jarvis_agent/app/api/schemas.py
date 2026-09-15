from typing import Any, Literal

from pydantic import BaseModel, Field


class WhatsAppMessage(BaseModel):
    phone: str = Field(min_length=1)
    type: Literal["text", "audio"]
    text: str | None = None
    audio_url: str | None = None


class WhatsAppWebhookRequest(BaseModel):
    phone: str | None = None
    type: Literal["text", "audio"] | None = None
    text: str | None = None
    audio_url: str | None = None
    data: dict[str, Any] | None = None


class WebhookResponse(BaseModel):
    ok: bool
    phone: str
    message: str
    forwarded: bool
