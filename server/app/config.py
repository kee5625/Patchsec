from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "server"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # Add your settings below
    # database_url: str
    # secret_key: str


settings = Settings()
