"""Settings read from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

QUELLVERZEICHNIS = Path(__file__).resolve().parent


class Einstellungen(BaseSettings):
    """Everything the server can be configured with, read from environment variables."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    cors_origins: str = "https://calltaker.emberbox.app,http://localhost:5173"
    frontend_verzeichnis: Path = QUELLVERZEICHNIS / "frontend_dist"
    daten_verzeichnis: Path = QUELLVERZEICHNIS.parent / ".daten"
    adressen_tage: int = 30
    adressen_laden: bool = True
    uebung_lebensdauer_stunden: float = 12
    uebungen_hoechstens: int = 500
    abfrage_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "abfrage"
    orte_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "orte"
    anleitungen_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "anleitungen"
    beschwerden_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "beschwerden"
    leitfragen_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "leitfragen"
    gefahrstoffe_verzeichnis: Path = QUELLVERZEICHNIS.parent / "daten" / "gefahrstoffe"

    def adressen_datei(self) -> Path:
        """Return where the address list is kept: in the data folder."""
        return self.daten_verzeichnis / "adressen.sqlite"

    def erlaubte_origins(self) -> list[str]:
        """Return the allowed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def einstellungen() -> Einstellungen:
    """Return the settings, read once per process."""
    return Einstellungen()
