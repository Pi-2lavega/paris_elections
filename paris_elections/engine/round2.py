"""Logique du second tour des municipales.

Au T2 la liste arrivée en tête (pluralité) reçoit la prime majoritaire,
puis répartition proportionnelle du solde entre listes ≥ 5%.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from paris_elections.config import SEUIL_PROPORTIONNELLE
from paris_elections.engine.allocation import allocate_with_bonus


@dataclass
class Round2Result:
    """Résultat du second tour pour un scrutin."""
    votes: Dict[str, int]
    total_expressed: int
    percentages: Dict[str, float]
    winner: str
    seats: Dict[str, int]


def run_round2(
    votes: Dict[str, int],
    total_seats: int,
    bonus_fraction: float,
) -> Round2Result:
    """Exécute le second tour d'un scrutin de liste.

    Au T2, la liste arrivée en tête obtient la prime puis la proportionnelle
    est répartie entre les listes ayant ≥ 5%.

    Args:
        votes: dict liste → nombre de voix (listes qualifiées uniquement).
        total_seats: sièges à répartir.
        bonus_fraction: fraction de la prime majoritaire.

    Returns:
        Round2Result.
    """
    total_expressed = sum(votes.values())

    if total_expressed == 0:
        raise ValueError("Aucun vote exprimé au T2.")

    pcts = {k: v / total_expressed for k, v in votes.items()}

    winner = max(pcts, key=pcts.get)  # type: ignore[arg-type]

    seats = allocate_with_bonus(
        votes, total_seats, bonus_fraction,
        winner=winner, threshold_pct=SEUIL_PROPORTIONNELLE,
    )

    return Round2Result(
        votes=votes,
        total_expressed=total_expressed,
        percentages=pcts,
        winner=winner,
        seats=seats,
    )
