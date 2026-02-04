"""Chargement unifié des données (APIs + CSV).

Point d'entrée unique pour accéder aux données électorales et démographiques.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from paris_elections.data.cache import ParquetCache
from paris_elections.data.opendata_paris import OpenDataParisClient
from paris_elections.data.insee import INSEEClient

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


class DataLoader:
    """Point d'entrée unifié pour le chargement des données."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache = ParquetCache(cache_dir or PROCESSED_DIR)
        self.opendata = OpenDataParisClient(cache=self.cache)
        self.insee = INSEEClient(cache=self.cache)

    # --- Données électorales ---

    def load_election(self, key: str) -> pd.DataFrame:
        """Charge les données d'une élection (API ou cache).

        Args:
            key: clé d'élection (ex. "municipales_2020_t1").

        Returns:
            DataFrame brut.
        """
        return self.opendata.get_election(key)

    def load_election_by_sector(self, key: str) -> pd.DataFrame:
        """Charge et agrège par secteur.

        Args:
            key: clé d'élection.

        Returns:
            DataFrame agrégé par secteur.
        """
        df = self.load_election(key)
        return self.opendata.aggregate_to_sectors(df)

    def load_csv(self, filename: str, subdir: str = "raw") -> pd.DataFrame:
        """Charge un CSV depuis le répertoire data/.

        Args:
            filename: nom du fichier.
            subdir: sous-répertoire ("raw" ou "processed").

        Returns:
            DataFrame.
        """
        base = RAW_DIR if subdir == "raw" else PROCESSED_DIR
        path = base / filename
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        return pd.read_csv(path)

    # --- Données démographiques ---

    def load_population(self) -> pd.DataFrame:
        """Population par arrondissement."""
        return self.insee.get_population()

    def load_population_by_sector(self) -> pd.DataFrame:
        """Population agrégée par secteur."""
        return self.insee.aggregate_to_sectors()

    # --- Utilitaires ---

    def available_elections(self) -> Dict[str, str]:
        """Liste les élections disponibles via l'API."""
        return self.opendata.list_datasets()

    def cache_status(self) -> dict:
        """État du cache."""
        return self.cache.list_entries()

    def clear_cache(self):
        """Vide le cache."""
        self.cache.clear()
