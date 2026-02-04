"""Client API opendata.paris.fr (Explore V2.1).

Datasets utilisés :
  - Municipales 2014/2020 (résultats par bureau de vote)
  - Présidentielle 2022 (T1 Paris)
  - Européennes 2024
  - Bureaux de vote (géographie)

L'API Explore V2.1 utilise un format REST :
  GET /api/explore/v2.1/catalog/datasets/{dataset_id}/records
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from paris_elections.config import ARRONDISSEMENT_TO_SECTEUR, SECTEURS
from paris_elections.data.cache import ParquetCache, TTL_API

logger = logging.getLogger(__name__)

BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"

# Mapping des datasets connus
DATASETS = {
    "municipales_2020_t1": "elections-municipales-2020-1er-tour",
    "municipales_2020_t2": "elections-municipales-2020-2nd-tour",
    "municipales_2014_t1": "elections-municipales-2014-1er-tour",
    "municipales_2014_t2": "elections-municipales-2014-2nd-tour",
    "presidentielle_2022_t1": "election-presidentielle-2022-resultats-du-1er-tour-par-bureau-de-vote",
    "europeennes_2024": "elections-europeennes-2024-resultats-par-bureau-de-vote",
}


class OpenDataParisClient:
    """Client pour l'API opendata.paris.fr."""

    def __init__(self, cache: Optional[ParquetCache] = None):
        self.cache = cache or ParquetCache()
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _fetch_records(
        self,
        dataset_id: str,
        limit: int = -1,
        where: Optional[str] = None,
    ) -> pd.DataFrame:
        """Récupère tous les enregistrements d'un dataset.

        Args:
            dataset_id: identifiant du dataset.
            limit: nombre max de records (-1 = tous).
            where: filtre ODSQL optionnel.

        Returns:
            DataFrame des records.
        """
        cache_key = f"opendata_paris_{dataset_id}"
        if where:
            cache_key += f"__{where}"

        cached = self.cache.get(cache_key, ttl=TTL_API)
        if cached is not None:
            logger.info("Cache hit pour %s", cache_key)
            return cached

        all_records: List[Dict[str, Any]] = []
        offset = 0
        page_size = 100

        while True:
            params: Dict[str, Any] = {
                "limit": page_size,
                "offset": offset,
            }
            if where:
                params["where"] = where

            url = f"{BASE_URL}/{dataset_id}/records"
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            if not results:
                break

            all_records.extend(results)
            offset += len(results)

            total = data.get("total_count", 0)
            if offset >= total:
                break
            if 0 < limit <= offset:
                break

        if not all_records:
            return pd.DataFrame()

        df = pd.json_normalize(all_records)
        self.cache.put(cache_key, df, source="opendata_paris")
        return df

    def get_election(self, election_key: str, **kwargs) -> pd.DataFrame:
        """Récupère les données d'une élection par clé.

        Args:
            election_key: clé dans DATASETS (ex. "municipales_2020_t1").

        Returns:
            DataFrame brut.
        """
        dataset_id = DATASETS.get(election_key)
        if not dataset_id:
            raise ValueError(
                f"Élection inconnue : {election_key}. "
                f"Clés disponibles : {list(DATASETS.keys())}"
            )
        return self._fetch_records(dataset_id, **kwargs)

    def aggregate_to_sectors(
        self,
        df: pd.DataFrame,
        arrondissement_col: str = "code_bv",
        score_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Agrège les données bureau de vote → secteur.

        Le parsing est robuste : tente de détecter automatiquement les colonnes
        de scores (numériques) si score_cols n'est pas fourni.

        Args:
            df: DataFrame au niveau bureau de vote.
            arrondissement_col: colonne contenant le code bureau (ex. "01_001").
            score_cols: colonnes numériques à sommer.

        Returns:
            DataFrame agrégé par secteur.
        """
        # Extraire le numéro d'arrondissement depuis le code bureau
        if arrondissement_col in df.columns:
            df = df.copy()
            df["_arr"] = df[arrondissement_col].astype(str).str[:2].astype(int)
        elif "arrondissement" in df.columns:
            df = df.copy()
            df["_arr"] = df["arrondissement"].astype(int)
        else:
            raise ValueError(
                f"Colonne arrondissement introuvable. Colonnes : {list(df.columns)}"
            )

        df["secteur"] = df["_arr"].map(ARRONDISSEMENT_TO_SECTEUR)

        # Auto-détection des colonnes de score
        if score_cols is None:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            exclude = {"_arr", "inscrits", "votants", "exprimes", "blancs", "nuls"}
            score_cols = [c for c in numeric_cols if c.lower() not in exclude]

        agg_cols = ["inscrits", "votants", "exprimes"] + score_cols
        agg_cols = [c for c in agg_cols if c in df.columns]

        return df.groupby("secteur")[agg_cols].sum().reset_index()

    def list_datasets(self) -> Dict[str, str]:
        """Liste les datasets électoraux disponibles."""
        return dict(DATASETS)
