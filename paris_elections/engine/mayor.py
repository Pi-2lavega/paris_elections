"""Simulation de l'élection du maire de Paris par le Conseil de Paris.

Règles :
  - Tour 1 : majorité absolue (82/163) requise
  - Tour 2 : majorité absolue requise
  - Tour 3 : pluralité suffit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from paris_elections.config import MAYOR_ROUNDS_MAX, MAYOR_ABSOLUTE_MAJORITY, CONSEIL_PARIS_SEATS


@dataclass
class MayorCandidate:
    """Candidat à l'élection du maire."""
    name: str
    coalition: str               # Identifiant de la coalition
    supporting_lists: List[str]  # Listes qui soutiennent ce candidat


@dataclass
class MayorElectionResult:
    """Résultat de l'élection du maire."""
    elected: Optional[str] = None
    round_elected: int = 0
    rounds: List[Dict[str, int]] = field(default_factory=list)


def simulate_mayor_election(
    seats_by_list: Dict[str, int],
    candidates: List[MayorCandidate],
    discipline_rate: float = 0.95,
) -> MayorElectionResult:
    """Simule l'élection du maire du Conseil de Paris.

    Chaque conseiller vote pour le candidat de sa coalition.
    Le taux de discipline modélise les défections éventuelles.

    Args:
        seats_by_list: dict liste → nombre de sièges au Conseil de Paris.
        candidates: candidats au poste de maire.
        discipline_rate: fraction de conseillers votant selon la consigne.

    Returns:
        MayorElectionResult.
    """
    result = MayorElectionResult()

    # Calculer les voix potentielles de chaque candidat
    def _count_votes(round_num: int) -> Dict[str, int]:
        votes = {}
        undisciplined_pool = 0

        for candidate in candidates:
            raw = sum(seats_by_list.get(lst, 0) for lst in candidate.supporting_lists)
            disciplined = round(raw * discipline_rate)
            undisciplined_pool += raw - disciplined
            votes[candidate.name] = disciplined

        # Les voix indisciplinées sont perdues (votes blancs/nuls)
        return votes

    for round_num in range(1, MAYOR_ROUNDS_MAX + 1):
        votes = _count_votes(round_num)
        result.rounds.append(dict(votes))

        top = max(votes, key=votes.get)  # type: ignore[arg-type]
        top_votes = votes[top]

        if round_num <= 2:
            # Majorité absolue requise
            if top_votes >= MAYOR_ABSOLUTE_MAJORITY:
                result.elected = top
                result.round_elected = round_num
                return result
        else:
            # Tour 3 : pluralité
            result.elected = top
            result.round_elected = round_num
            return result

    return result


def simple_mayor_check(
    seats_by_list: Dict[str, int],
    coalitions: Dict[str, List[str]],
) -> Dict[str, Tuple[int, bool]]:
    """Vérifie rapidement quelle coalition atteint la majorité.

    Args:
        seats_by_list: dict liste → sièges.
        coalitions: dict nom_coalition → listes membres.

    Returns:
        dict coalition → (total_sièges, a_la_majorité).
    """
    results = {}
    for coalition_name, lists in coalitions.items():
        total = sum(seats_by_list.get(lst, 0) for lst in lists)
        results[coalition_name] = (total, total >= MAYOR_ABSOLUTE_MAJORITY)
    return results
