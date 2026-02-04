"""Logique entre les deux tours : fusions, retraits, transferts de voix.

Modélisation des dynamiques d'entre-deux-tours :
  - Fusions de listes (liste absorbée par une liste qualifiée)
  - Retraits avec report de voix paramétrable
  - Détection de triangulaires / quadrangulaires
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from paris_elections.config import DEFAULT_TRANSFER_RATE


@dataclass
class Fusion:
    """Fusion d'une liste dans une autre."""
    absorbed: str          # Liste absorbée (fusionable, 5-10%)
    into: str              # Liste qualifiée réceptrice
    transfer_rate: float = DEFAULT_TRANSFER_RATE


@dataclass
class Withdrawal:
    """Retrait d'une liste qualifiée (désistement / front républicain)."""
    withdrawing: str       # Liste qui se retire
    beneficiaries: Dict[str, float] = field(default_factory=dict)
    # dict liste → fraction des voix transférées (somme ≤ 1, reste = abstention)


@dataclass
class InterRoundConfig:
    """Configuration des dynamiques d'entre-deux-tours."""
    fusions: List[Fusion] = field(default_factory=list)
    withdrawals: List[Withdrawal] = field(default_factory=list)
    # Variation de participation T1 → T2 (ex. +0.02 = +2 pts)
    participation_delta: float = 0.0


@dataclass
class Round2Setup:
    """Données préparées pour le second tour."""
    lists_in_round2: List[str]
    estimated_votes: Dict[str, int]
    is_triangulaire: bool = False
    is_quadrangulaire: bool = False


def apply_interround(
    round1_votes: Dict[str, int],
    qualified: List[str],
    fusionable: List[str],
    eliminated: List[str],
    config: InterRoundConfig,
    inscrits: int,
    participation_t1: float,
) -> Round2Setup:
    """Applique les fusions et retraits pour préparer le T2.

    Args:
        round1_votes: votes du T1 par liste.
        qualified: listes qualifiées (≥10%).
        fusionable: listes pouvant fusionner (5-10%).
        eliminated: listes éliminées (<5%).
        config: configuration des fusions / retraits.
        inscrits: nombre d'inscrits.
        participation_t1: taux de participation au T1.

    Returns:
        Round2Setup avec votes estimés pour le T2.
    """
    # Commencer avec les votes T1 des listes qualifiées
    votes_t2: Dict[str, float] = {q: float(round1_votes.get(q, 0)) for q in qualified}

    # Appliquer les fusions
    absorbed_lists = set()
    for fusion in config.fusions:
        if fusion.absorbed in fusionable and fusion.into in votes_t2:
            transfer = round1_votes.get(fusion.absorbed, 0) * fusion.transfer_rate
            votes_t2[fusion.into] += transfer
            absorbed_lists.add(fusion.absorbed)

    # Voix des fusionables non absorbés → perdues (abstention)
    # (elles ne sont pas qualifiées et ne fusionnent avec personne)

    # Appliquer les retraits
    withdrawn_lists = set()
    for withdrawal in config.withdrawals:
        if withdrawal.withdrawing in votes_t2:
            base_votes = votes_t2.pop(withdrawal.withdrawing)
            withdrawn_lists.add(withdrawal.withdrawing)
            for beneficiary, fraction in withdrawal.beneficiaries.items():
                if beneficiary in votes_t2:
                    votes_t2[beneficiary] += base_votes * fraction

    # Ajustement de la participation T2
    participation_t2 = participation_t1 + config.participation_delta
    participation_t2 = max(0.0, min(1.0, participation_t2))

    # Recalculer les votes absolus en fonction de la nouvelle participation
    total_t1 = sum(round1_votes.values())
    total_t2_target = inscrits * participation_t2
    if total_t1 > 0:
        ratio = total_t2_target / sum(votes_t2.values()) if sum(votes_t2.values()) > 0 else 1.0
        votes_t2 = {k: v * ratio for k, v in votes_t2.items()}

    # Arrondir
    estimated = {k: round(v) for k, v in votes_t2.items()}

    lists_in = sorted(estimated.keys(), key=lambda k: estimated[k], reverse=True)

    return Round2Setup(
        lists_in_round2=lists_in,
        estimated_votes=estimated,
        is_triangulaire=len(lists_in) == 3,
        is_quadrangulaire=len(lists_in) >= 4,
    )


def auto_fusions(
    fusionable: List[str],
    qualified: List[str],
    alliances: Dict[str, str],
    transfer_rate: float = DEFAULT_TRANSFER_RATE,
) -> List[Fusion]:
    """Génère automatiquement les fusions basées sur les alliances déclarées.

    Args:
        fusionable: listes pouvant fusionner.
        qualified: listes qualifiées.
        alliances: dict liste_fusionable → liste_qualifiée préférée.
        transfer_rate: taux de transfert par défaut.

    Returns:
        Liste de Fusion.
    """
    fusions = []
    for f_list in fusionable:
        target = alliances.get(f_list)
        if target and target in qualified:
            fusions.append(Fusion(absorbed=f_list, into=target, transfer_rate=transfer_rate))
    return fusions
