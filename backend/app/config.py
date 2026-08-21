from pathlib import Path

from pydantic import model_validator
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
    app_env: str = "development"
    cookie_name: str = "learn_session"
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    login_challenge_ttl_sec: int = 300
    challenge_cookie_name: str = "learn_2fa_challenge"
    upload_dir: str = "/app/uploads"
    redis_url: str = "redis://redis:6379/0"
    # Brute-Force / Login-Schutz (Redis)
    login_allowlist_only: bool = True
    login_rate_limit_per_ip: int = 15
    login_rate_limit_window_sec: int = 60
    login_2fa_rate_limit_per_ip: int = 20
    login_max_failures_per_ip: int = 8
    login_max_failures_per_email: int = 5
    login_fail_window_sec: int = 900
    login_ip_block_ttl_sec: int = 3600
    login_email_block_ttl_sec: int = 1800
    login_unknown_block_ttl_sec: int = 0  # 0 = 10 Jahre (praktisch dauerhaft)
    login_unknown_ip_block_ttl_sec: int = 0  # 0 = wie unknown_block_ttl
    login_2fa_max_failures_per_ip: int = 10
    # Kommasepariert: Docker/nginx — nur von diesen Hops X-Forwarded-For vertrauen
    trusted_proxy_cidrs: str = "127.0.0.0/8,172.16.0.0/12,10.0.0.0/8,192.168.0.0/16"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # Lokaler Whisper (OpenAI-kompatibel), z. B. faster-whisper auf GMKtec :9000
    whisper_url: str = ""
    whisper_api_key: str = ""
    ollama_url: str = "http://host.docker.internal:11434"
    tts_provider: str = "openai"
    llm_provider: str = "ollama"
    ollama_model: str = ""
    ollama_vision_model: str = ""
    ollama_chat_timeout_sec: int = 900
    ollama_vision_timeout_sec: int = 900
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-sonnet-4-0"
    generate_max_active_per_user: int = 2
    generate_max_active_per_tenant: int = 5
    generate_rate_limit_per_user_hour: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @model_validator(mode="after")
    def enforce_production_defaults(self) -> "Settings":
        if self.is_production and not self.cookie_secure:
            object.__setattr__(self, "cookie_secure", True)
        return self


settings = Settings()
