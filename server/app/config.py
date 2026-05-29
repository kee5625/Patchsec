from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "server"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    github_token: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"


settings = Settings()
