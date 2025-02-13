from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    MINIO_CLIENT_LINK: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str
    BASE_URL: str
    SQLALCHEMY_DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Config()
