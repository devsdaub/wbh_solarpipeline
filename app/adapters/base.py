from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class SourceAdapter(ABC):

    name: str

    @abstractmethod
    def fetch(self, start: date, end: date) -> pd.DataFrame:
        """Holt Rohdaten der Quelle für den angegebenen Zeitraum."""