import logging
import time

import httpx

logger = logging.getLogger(__name__)

VERSUCHE = 3
BASIS_SEKUNDEN = 1.0


def mit_wiederholung(aufruf, versuche: int = VERSUCHE) -> httpx.Response:
    """Führt einen HTTP-Aufruf aus und wiederholt ihn bei Fehlern."""
    for versuch in range(1, versuche + 1):
        try:
            antwort = aufruf()
            antwort.raise_for_status()
            return antwort
        except httpx.HTTPError as fehler:
            if versuch == versuche:
                raise
            wartezeit = BASIS_SEKUNDEN * 2 ** (versuch - 1)
            logger.warning(
                "Versuch %s von %s fehlgeschlagen (%s), erneut in %.0f s",
                versuch, versuche, _kurzform(fehler), wartezeit,
            )
            time.sleep(wartezeit)


def _kurzform(fehler: Exception) -> str:
    if isinstance(fehler, httpx.HTTPStatusError):
        return f"HTTP {fehler.response.status_code}"
    return type(fehler).__name__
