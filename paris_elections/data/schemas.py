"""Modèles Pydantic pour la validation des données électorales."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BureauDeVoteResult(BaseModel):
    """Résultat d'un bureau de vote pour une élection."""
    bureau_id: str
    arrondissement: int = Field(ge=1, le=20)
    inscrits: int = Field(ge=0)
    votants: int = Field(ge=0)
    exprimes: int = Field(ge=0)
    blancs: int = Field(ge=0, default=0)
    nuls: int = Field(ge=0, default=0)
    scores: Dict[str, int] = Field(default_factory=dict)
    # scores : dict nom_liste → nombre de voix

    @field_validator("exprimes")
    @classmethod
    def exprimes_le_votants(cls, v, info):
        votants = info.data.get("votants", 0)
        if v > votants:
            raise ValueError(f"exprimés ({v}) > votants ({votants})")
        return v


class SectorResult(BaseModel):
    """Résultat agrégé pour un secteur."""
    secteur: str
    arrondissements: List[int]
    inscrits: int = Field(ge=0)
    votants: int = Field(ge=0)
    exprimes: int = Field(ge=0)
    scores: Dict[str, int] = Field(default_factory=dict)
    percentages: Dict[str, float] = Field(default_factory=dict)

    @property
    def participation(self) -> float:
        return self.votants / self.inscrits if self.inscrits > 0 else 0.0


class INSEEProfile(BaseModel):
    """Profil démographique INSEE d'un arrondissement."""
    code_commune: str  # 75101..75120
    arrondissement: int
    population: int = Field(ge=0)
    pop_0_14: float = Field(ge=0, le=1, default=0)
    pop_15_29: float = Field(ge=0, le=1, default=0)
    pop_30_44: float = Field(ge=0, le=1, default=0)
    pop_45_59: float = Field(ge=0, le=1, default=0)
    pop_60_74: float = Field(ge=0, le=1, default=0)
    pop_75_plus: float = Field(ge=0, le=1, default=0)
    revenu_median: Optional[float] = None
    taux_cadres: Optional[float] = None
    taux_diplomes_sup: Optional[float] = None
    taux_proprietaires: Optional[float] = None


class PollEntry(BaseModel):
    """Entrée de sondage pour une liste."""
    source: str           # Institut / média
    date: str             # ISO date
    election: str         # "municipales_2026", etc.
    liste: str
    family: Optional[str] = None
    score_brut: float = Field(ge=0, le=100)
    score_redresse: Optional[float] = None
    sample_size: Optional[int] = None
    margin_error: Optional[float] = None


class ElectionDataset(BaseModel):
    """Jeu de données pour une élection."""
    election: str                    # "municipales_2020", "presidentielle_2022_t1", etc.
    date: str
    bureaux: List[BureauDeVoteResult] = Field(default_factory=list)
    sectors: List[SectorResult] = Field(default_factory=list)
