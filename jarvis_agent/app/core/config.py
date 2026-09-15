from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    waha_server_url: str = "http://localhost:3000"
    waha_session: str = "default"
    n8n_webhook_url: str = ""
    stt_language: str = "pt-BR"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
