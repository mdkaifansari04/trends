from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    ingest_api_key: str


def get_settings() -> Settings:
    return Settings(ingest_api_key=os.getenv("INGEST_API_KEY", ""))
