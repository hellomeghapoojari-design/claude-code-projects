from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    eventbrite_token: str = ""
    meetup_token: str = ""
    database_url: str = "sqlite:///./events.db"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
