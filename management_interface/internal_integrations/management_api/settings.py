from functools import lru_cache

from pydantic import BaseSettings


class ManagementAPISettings(BaseSettings):
    base_url: str

    class Config:
        env_prefix = "MANAGEMENT_API_"


@lru_cache(maxsize=1)
def get_management_api_settings() -> ManagementAPISettings:
    return ManagementAPISettings()
