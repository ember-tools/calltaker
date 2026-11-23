"""Settings read from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

QUELLVERZEICHNIS = Path(__file__).resolve().parent


class Einstellungen(BaseSettings):
    """Everything the server can be configured with, read from environment variables."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    cors_origins: str = "https://calltaker.chojo.dev,http://localhost:5173"
    frontend_verzeichnis: Path = QUELLVERZEICHNIS / "frontend_dist"
    daten_verzeichnis: Path = Path("/data")
    abfrage_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "abfrage"

    def erlaubte_origins(self) -> list[str]:
        """Return the allowed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def einstellungen() -> Einstellungen:
    """Return the settings, read once per process."""
    return Einstellungen()
