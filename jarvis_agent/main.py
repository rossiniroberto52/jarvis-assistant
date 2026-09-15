import logging

from fastapi import FastAPI

from app.api.whatsapp import router as whatsapp_router
from app.core.config import settings

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Jarvis Gateway", version="1.0.0")
app.include_router(whatsapp_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
