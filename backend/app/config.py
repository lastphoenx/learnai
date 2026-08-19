from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_ENV, _BACKEND_ENV),
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://learnai:learnai@localhost:5433/learnai"
    encryption_master_key: str = ""
    session_secret: str = ""
    session_ttl_sec: int = 28800
    pbkdf2_iterations: int = 600_000
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    default_tenant_slug: str = "default"
    allow_registration: bool = False
    cookie_name: str = "learn_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    login_challenge_ttl_sec: int = 300
    challenge_cookie_name: str = "learn_2fa_challenge"
    upload_dir: str = "/app/uploads"
    redis_url: str = "redis://redis:6379/0"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_url: str = "http://192.168.131.60:11434"
    tts_provider: str = "openai"
    llm_provider: str = "ollama"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-sonnet-4-0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
