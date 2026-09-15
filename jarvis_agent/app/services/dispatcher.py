import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


async def forward_to_n8n(phone: str, message: str) -> dict:
    payload = {"phone": phone, "message": message}

    if not settings.n8n_webhook_url:
        log.error("N8N_WEBHOOK_URL não configurada")
        return {"ok": False, "error": "N8N_WEBHOOK_URL não configurada"}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(settings.n8n_webhook_url, json=payload)
        r.raise_for_status()

    log.info("n8n respondeu %s para phone=%s", r.status_code, phone)
    return {"ok": True, "status_code": r.status_code, "body": r.text}
