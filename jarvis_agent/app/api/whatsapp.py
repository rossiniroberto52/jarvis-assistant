import logging
from fastapi import APIRouter, HTTPException, status

from app.api.schemas import WhatsAppMessage, WhatsAppWebhookRequest, WebhookResponse
from app.services.dispatcher import forward_to_n8n
from app.services.stt import transcribe_url

router = APIRouter(prefix="/webhook", tags=["whatsapp"])
log = logging.getLogger(__name__)


def normalize_payload(payload: WhatsAppWebhookRequest) -> WhatsAppMessage:
    source = payload.data or {}
    phone = payload.phone or source.get("phone") or source.get("from")
    message_type = payload.type or source.get("type")
    text = payload.text or source.get("text") or source.get("body")
    audio_url = payload.audio_url or source.get("audio_url") or source.get("url")

    if not phone or message_type not in {"text", "audio"}:
        raise HTTPException(status_code=422, detail="phone e type são obrigatórios")
    if message_type == "text" and not text:
        raise HTTPException(status_code=422, detail="text é obrigatório para mensagens de texto")
    if message_type == "audio" and not audio_url:
        raise HTTPException(status_code=422, detail="audio_url é obrigatório para mensagens de áudio")

    return WhatsAppMessage(phone=phone, type=message_type, text=text, audio_url=audio_url)


@router.post("/whatsapp", response_model=WebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def receive_whatsapp(payload: WhatsAppWebhookRequest) -> WebhookResponse:
    message = normalize_payload(payload)
    clean_message = message.text.strip() if message.type == "text" else await transcribe_url(message.audio_url or "")

    if not clean_message:
        raise HTTPException(status_code=422, detail="Não foi possível extrair texto da mensagem")

    result = await forward_to_n8n(message.phone, clean_message)
    if not result["ok"]:
        raise HTTPException(status_code=503, detail=result["error"])

    log.info("Mensagem %s encaminhada para n8n", message.type)
    return WebhookResponse(ok=True, phone=message.phone, message=clean_message, forwarded=True)
