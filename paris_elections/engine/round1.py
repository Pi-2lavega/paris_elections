"""Logique du premier tour des municipales.

Règles :
  - Si une liste obtient > 50% des suffrages exprimés → élue au T1
    (prime majoritaire + proportionnelle)
  - Sinon : qualification T2 (≥10%), fusion possible (5-10%), éliminé (<5%)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from paris_elections.config import (
    SEUIL_VICTOIRE_T1,
    SEUIL_QUALIFICATION_T2,
    SEUIL_FUSION,
)
from paris_elections.engine.allocation import allocate_with_bonus


@dataclass
class Round1Result:
    """Résultat du premier tour pour un scrutin."""
    votes: Dict[str, int]
    total_expressed: int
    percentages: Dict[str, float]

    resolved: bool = False
    winner: Optional[str] = None
    seats: Optional[Dict[str, int]] = None

    qualified: List[str] = field(default_factory=list)       # ≥ 10% → T2
    fusionable: List[str] = field(default_factory=list)      # 5-10% → peut fusionner
    eliminated: List[str] = field(default_factory=list)       # < 5%


def run_round1(
    votes: Dict[str, int],
    total_seats: int,
    bonus_fraction: float,
) -> Round1Result:
    """Exécute le premier tour d'un scrutin de liste.

    Args:
        votes: dict liste → nombre de voix.
        total_seats: sièges à répartir.
        bonus_fraction: fraction de la prime majoritaire (0.25 ou 0.50).

    Returns:
        Round1Result avec qualification ou résolution.
    """
    total_expressed = sum(votes.values())

    if total_expressed == 0:
        return Round1Result(
            votes=votes,
            total_expressed=0,
            percentages={k: 0.0 for k in votes},
        )

    pcts = {k: v / total_expressed for k, v in votes.items()}

    result = Round1Result(
        votes=votes,
        total_expressed=total_expressed,
        percentages=pcts,
    )

    # Vérifier si une liste a la majorité absolue
    top_list = max(pcts, key=pcts.get)  # type: ignore[arg-type]
    if pcts[top_list] > SEUIL_VICTOIRE_T1:
        result.resolved = True
        result.winner = top_list
        result.seats = allocate_with_bonus(
            votes, total_seats, bonus_fraction, winner=top_list,
        )
        return result

    # Classification des listes
    for name, pct in pcts.items():
        if pct >= SEUIL_QUALIFICATION_T2:
            result.qualified.append(name)
        elif pct >= SEUIL_FUSION:
            result.fusionable.append(name)
        else:
            result.eliminated.append(name)

    return result
