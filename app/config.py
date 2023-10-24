from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LitScenes"
    openai_api_key: str
    db_connection: str
    celery_broker_url: str
    celery_result_backend: str
    redis_url: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()