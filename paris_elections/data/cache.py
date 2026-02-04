"""Cache local parquet avec TTL.

Stratégie :
  - Données API (opendata.paris, INSEE) : TTL 24h
  - Fichiers manuels (CSV uploadés) : TTL infini
  - Format : parquet (via pyarrow)
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd

# Répertoire par défaut du cache
_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

# TTL en secondes
TTL_API = 24 * 3600       # 24h pour les données API
TTL_INFINITE = float("inf")  # Pas d'expiration


class ParquetCache:
    """Cache de DataFrames en format parquet avec TTL."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._meta_file = self.cache_dir / "_cache_meta.json"
        self._meta = self._load_meta()

    def _load_meta(self) -> dict:
        if self._meta_file.exists():
            return json.loads(self._meta_file.read_text())
        return {}

    def _save_meta(self):
        self._meta_file.write_text(json.dumps(self._meta, indent=2))

    def _key_to_filename(self, key: str) -> str:
        h = hashlib.md5(key.encode()).hexdigest()[:12]
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return f"{safe_key[:60]}_{h}.parquet"

    def get(self, key: str, ttl: float = TTL_API) -> Optional[pd.DataFrame]:
        """Récupère un DataFrame du cache si présent et non expiré."""
        filename = self._key_to_filename(key)
        filepath = self.cache_dir / filename

        if not filepath.exists():
            return None

        meta = self._meta.get(key, {})
        cached_at = meta.get("cached_at", 0)

        if ttl != float("inf") and (time.time() - cached_at) > ttl:
            filepath.unlink(missing_ok=True)
            self._meta.pop(key, None)
            self._save_meta()
            return None

        return pd.read_parquet(filepath)

    def put(self, key: str, df: pd.DataFrame, source: str = "api"):
        """Stocke un DataFrame dans le cache."""
        filename = self._key_to_filename(key)
        filepath = self.cache_dir / filename

        df.to_parquet(filepath, index=False)

        self._meta[key] = {
            "filename": filename,
            "cached_at": time.time(),
            "source": source,
            "rows": len(df),
        }
        self._save_meta()

    def invalidate(self, key: str):
        """Supprime une entrée du cache."""
        filename = self._key_to_filename(key)
        filepath = self.cache_dir / filename
        filepath.unlink(missing_ok=True)
        self._meta.pop(key, None)
        self._save_meta()

    def clear(self):
        """Vide tout le cache."""
        for f in self.cache_dir.glob("*.parquet"):
            f.unlink()
        self._meta.clear()
        self._save_meta()

    def list_entries(self) -> dict:
        """Liste toutes les entrées du cache."""
        return dict(self._meta)
