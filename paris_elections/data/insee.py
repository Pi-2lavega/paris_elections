"""Client données INSEE par arrondissement parisien.

Sources :
  - API INSEE (si authentification disponible)
  - Fallback : data.gouv.fr + fichiers CSV manuels + cache local

Codes commune : 75101..75120
Agrégation 1er-4e → Paris Centre (moyennes pondérées par population)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from paris_elections.config import ARRONDISSEMENT_INSEE, SECTEURS
from paris_elections.data.cache import ParquetCache, TTL_API, TTL_INFINITE
from paris_elections.data.schemas import INSEEProfile

logger = logging.getLogger(__name__)

# Données de référence (population légale 2021, source INSEE)
# À remplacer par des données API/CSV plus complètes
POPULATION_2021: Dict[int, int] = {
    1: 16_266,    2: 20_454,    3: 34_115,    4: 28_088,
    5: 58_850,    6: 41_345,    7: 48_907,    8: 35_837,
    9: 60_324,   10: 86_281,   11: 146_643,  12: 140_296,
    13: 181_533,  14: 135_964,  15: 233_392,  16: 166_361,
    17: 167_288,  18: 195_060,  19: 187_543,  20: 196_649,
}

RAW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


class INSEEClient:
    """Client pour les données démographiques INSEE des arrondissements parisiens."""

    def __init__(self, cache: Optional[ParquetCache] = None):
        self.cache = cache or ParquetCache()

    def get_population(self) -> pd.DataFrame:
        """Population par arrondissement (données 2021).

        Returns:
            DataFrame avec colonnes : arrondissement, code_commune, population.
        """
        cache_key = "insee_population_paris"
        cached = self.cache.get(cache_key, ttl=TTL_INFINITE)
        if cached is not None:
            return cached

        # Essayer de charger un CSV local
        csv_path = RAW_DATA_DIR / "population_arrondissements.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            self.cache.put(cache_key, df, source="csv_local")
            return df

        # Fallback : données intégrées
        records = []
        for arr, pop in POPULATION_2021.items():
            records.append({
                "arrondissement": arr,
                "code_commune": ARRONDISSEMENT_INSEE[arr],
                "population": pop,
            })
        df = pd.DataFrame(records)
        self.cache.put(cache_key, df, source="builtin")
        return df

    def get_profiles(self) -> List[INSEEProfile]:
        """Profils démographiques par arrondissement.

        Returns:
            Liste d'INSEEProfile (données partielles si CSV absent).
        """
        pop_df = self.get_population()
        profiles = []
        for _, row in pop_df.iterrows():
            profiles.append(INSEEProfile(
                code_commune=ARRONDISSEMENT_INSEE[row["arrondissement"]],
                arrondissement=row["arrondissement"],
                population=row["population"],
            ))
        return profiles

    def aggregate_to_sectors(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Agrège les données par secteur (Paris Centre = 1er-4e).

        Args:
            df: DataFrame avec colonne 'arrondissement'. Si None, utilise population.

        Returns:
            DataFrame agrégé par secteur.
        """
        if df is None:
            df = self.get_population()

        from paris_elections.config import ARRONDISSEMENT_TO_SECTEUR
        df = df.copy()
        df["secteur"] = df["arrondissement"].map(ARRONDISSEMENT_TO_SECTEUR)

        # Agréger : somme pour les comptages, moyenne pondérée pour les taux
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        rate_cols = [c for c in numeric_cols if c.startswith(("taux_", "pop_", "revenu_"))]
        sum_cols = [c for c in numeric_cols if c not in rate_cols and c != "arrondissement"]

        agg = {}
        for c in sum_cols:
            agg[c] = "sum"
        for c in rate_cols:
            # Moyenne pondérée par la population
            agg[c] = lambda x, col=c: (
                (x * df.loc[x.index, "population"]).sum() /
                df.loc[x.index, "population"].sum()
            ) if "population" in df.columns else x.mean()

        return df.groupby("secteur").agg(agg).reset_index()

    def load_csv(self, path: str, key: str = "insee_custom") -> pd.DataFrame:
        """Charge un CSV INSEE manuellement et le cache.

        Args:
            path: chemin vers le fichier CSV.
            key: clé de cache.

        Returns:
            DataFrame.
        """
        df = pd.read_csv(path)
        self.cache.put(key, df, source="csv_manual")
        return df
