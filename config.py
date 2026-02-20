import json
from typing import Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_api_version: str = Field(default="2025-04-01-preview", alias="AZURE_API_VERSION")
    model_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "claude-opus-4-5-20251101": "gpt-4o",
            "claude-sonnet-4-5-20250929": "gpt-4o-mini"
        },
        alias="MODEL_MAPPING"
    )
    timeout: int = Field(default=120)
    debug: bool = Field(default=False)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse MODEL_MAPPING if it's a string (from env var)
        if isinstance(self.model_mapping, str):
            self.model_mapping = json.loads(self.model_mapping)


_config = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
