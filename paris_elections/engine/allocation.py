"""Algorithme D'Hondt (plus forte moyenne) et allocation avec prime majoritaire.

Références :
  - Code électoral, art. L262 (répartition proportionnelle à la plus forte moyenne)
  - Réforme 2025 : prime 25% Conseil de Paris, 50% conseils d'arrondissement
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math


def plus_forte_moyenne(
    votes: Dict[str, int],
    total_seats: int,
    threshold_pct: float = 0.0,
) -> Dict[str, int]:
    """Répartition proportionnelle à la plus forte moyenne (D'Hondt).

    Args:
        votes: dict liste → nombre de voix.
        total_seats: nombre de sièges à répartir.
        threshold_pct: seuil minimal (en fraction, ex. 0.05 pour 5%)
                       pour participer à la répartition.

    Returns:
        dict liste → nombre de sièges attribués.
    """
    if total_seats <= 0:
        return {k: 0 for k in votes}

    total_votes = sum(votes.values())
    if total_votes == 0:
        return {k: 0 for k in votes}

    # Filtrer les listes sous le seuil
    eligible = {
        k: v for k, v in votes.items()
        if v / total_votes >= threshold_pct
    }

    if not eligible:
        # Aucune liste éligible → répartir entre toutes (cas dégénéré)
        eligible = dict(votes)

    seats: Dict[str, int] = {k: 0 for k in eligible}

    for _ in range(total_seats):
        # Moyenne = voix / (sièges déjà attribués + 1)
        best_list = max(eligible, key=lambda k: eligible[k] / (seats[k] + 1))
        seats[best_list] += 1

    # Ajouter les listes non éligibles avec 0 sièges
    result = {k: 0 for k in votes}
    result.update(seats)
    return result


def allocate_with_bonus(
    votes: Dict[str, int],
    total_seats: int,
    bonus_fraction: float,
    winner: Optional[str] = None,
    threshold_pct: float = 0.05,
) -> Dict[str, int]:
    """Allocation avec prime majoritaire puis proportionnelle sur le reste.

    La liste arrivée en tête reçoit la prime (arrondie) puis participe
    aussi à la répartition proportionnelle du solde.

    Args:
        votes: dict liste → nombre de voix.
        total_seats: nombre total de sièges.
        bonus_fraction: fraction du total constituant la prime (ex. 0.25).
        winner: liste gagnante (si None, déterminée par le score le plus élevé).
        threshold_pct: seuil pour la proportionnelle (défaut 5%).

    Returns:
        dict liste → nombre de sièges.
    """
    if not votes or total_seats <= 0:
        return {k: 0 for k in votes}

    if winner is None:
        winner = max(votes, key=votes.get)  # type: ignore[arg-type]

    bonus_seats = round(total_seats * bonus_fraction)
    proportional_seats = total_seats - bonus_seats

    # Répartition proportionnelle du solde (toutes listes ≥ seuil)
    prop_alloc = plus_forte_moyenne(votes, proportional_seats, threshold_pct)

    # Ajout de la prime
    result = dict(prop_alloc)
    result[winner] = result.get(winner, 0) + bonus_seats

    return result


def compute_quotient_table(
    votes: Dict[str, int],
    max_divisor: int = 20,
) -> List[Tuple[str, int, float]]:
    """Table des quotients D'Hondt (utile pour le débogage / visualisation).

    Returns:
        Liste de (liste, diviseur, quotient) triée par quotient décroissant.
    """
    table = []
    for name, v in votes.items():
        for d in range(1, max_divisor + 1):
            table.append((name, d, v / d))
    table.sort(key=lambda x: x[2], reverse=True)
    return table
