from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    openai_api_key: str
    db_connection: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()