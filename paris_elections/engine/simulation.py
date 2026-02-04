"""Orchestrateur complet de la simulation électorale.

Enchaîne :
  1. Conversion % → votes absolus
  2. Simulation Conseil de Paris (scrutin de liste parisien, prime 25%)
  3. Simulation des 17 conseils d'arrondissement (scrutins sectoriels, prime 50%)
  4. Si pas résolu au T1 → inter-tour → T2
  5. Simulation élection du maire
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from paris_elections.config import (
    SECTEURS,
    CONSEIL_PARIS_SEATS,
    CONSEIL_PARIS_BONUS_FRACTION,
    CONSEIL_ARRONDISSEMENT_SEATS,
    CONSEIL_ARRONDISSEMENT_BONUS_FRACTION,
    SEUIL_PROPORTIONNELLE,
    PARTICIPATION_DEFAUT,
    warn_provisional_seats,
)
from paris_elections.engine.round1 import Round1Result, run_round1
from paris_elections.engine.round2 import Round2Result, run_round2
from paris_elections.engine.interround import (
    InterRoundConfig,
    Round2Setup,
    apply_interround,
)
from paris_elections.engine.mayor import (
    MayorCandidate,
    MayorElectionResult,
    simulate_mayor_election,
    simple_mayor_check,
)


@dataclass
class ScrutinResult:
    """Résultat complet d'un scrutin (T1 + éventuellement T2)."""
    name: str
    total_seats: int
    round1: Round1Result
    interround: Optional[Round2Setup] = None
    round2: Optional[Round2Result] = None

    @property
    def seats(self) -> Dict[str, int]:
        if self.round1.resolved:
            return self.round1.seats or {}
        if self.round2:
            return self.round2.seats
        return {}

    @property
    def winner(self) -> Optional[str]:
        if self.round1.resolved:
            return self.round1.winner
        if self.round2:
            return self.round2.winner
        return None

    @property
    def resolved(self) -> bool:
        return self.round1.resolved or self.round2 is not None


@dataclass
class ElectionResult:
    """Résultat complet de l'élection (Conseil de Paris + arrondissements)."""
    conseil_paris: ScrutinResult
    arrondissements: Dict[str, ScrutinResult]
    mayor: Optional[MayorElectionResult] = None

    @property
    def total_seats_conseil(self) -> Dict[str, int]:
        return self.conseil_paris.seats

    def seats_summary(self) -> Dict[str, Dict[str, int]]:
        """Résumé des sièges : Conseil de Paris + chaque arrondissement."""
        summary = {"Conseil de Paris": self.conseil_paris.seats}
        for name, r in self.arrondissements.items():
            summary[name] = r.seats
        return summary


class ElectionSimulator:
    """Orchestrateur de simulation des municipales parisiennes."""

    def __init__(self):
        warn_provisional_seats()

    def scores_to_votes(
        self,
        scores_pct: Dict[str, float],
        inscrits: int,
        participation: float,
    ) -> Dict[str, int]:
        """Convertit des pourcentages en votes absolus.

        Args:
            scores_pct: dict liste → pourcentage (0-1 ou 0-100).
            inscrits: nombre d'inscrits.
            participation: taux de participation (0-1).

        Returns:
            dict liste → nombre de voix.
        """
        # Normaliser si les scores sont en pourcentage 0-100
        total_pct = sum(scores_pct.values())
        if total_pct > 2.0:
            # Probablement en %, convertir en fraction
            scores_pct = {k: v / 100.0 for k, v in scores_pct.items()}
            total_pct = sum(scores_pct.values())

        # Renormaliser à exactement 100%
        if total_pct > 0:
            factor = 1.0 / total_pct
            scores_pct = {k: v * factor for k, v in scores_pct.items()}

        exprimes = round(inscrits * participation)
        votes = {k: round(v * exprimes) for k, v in scores_pct.items()}

        # Ajuster pour que la somme corresponde exactement
        diff = exprimes - sum(votes.values())
        if diff != 0 and votes:
            top = max(votes, key=votes.get)  # type: ignore[arg-type]
            votes[top] += diff

        return votes

    def simulate_scrutin(
        self,
        name: str,
        votes: Dict[str, int],
        total_seats: int,
        bonus_fraction: float,
        interround_config: Optional[InterRoundConfig] = None,
        inscrits: int = 0,
        participation: float = PARTICIPATION_DEFAUT,
    ) -> ScrutinResult:
        """Simule un scrutin complet (T1 + éventuel T2).

        Args:
            name: nom du scrutin (ex. "Conseil de Paris").
            votes: dict liste → nombre de voix au T1.
            total_seats: sièges à répartir.
            bonus_fraction: fraction de la prime majoritaire.
            interround_config: config des fusions / retraits (None = auto).
            inscrits: nombre d'inscrits (pour calcul T2).
            participation: taux de participation T1.

        Returns:
            ScrutinResult.
        """
        r1 = run_round1(votes, total_seats, bonus_fraction)

        result = ScrutinResult(name=name, total_seats=total_seats, round1=r1)

        if r1.resolved:
            return result

        # Préparer le T2
        if interround_config is None:
            interround_config = InterRoundConfig()

        if inscrits <= 0:
            inscrits = round(sum(votes.values()) / participation) if participation > 0 else sum(votes.values())

        r2_setup = apply_interround(
            round1_votes=r1.votes,
            qualified=r1.qualified,
            fusionable=r1.fusionable,
            eliminated=r1.eliminated,
            config=interround_config,
            inscrits=inscrits,
            participation_t1=participation,
        )
        result.interround = r2_setup

        if r2_setup.estimated_votes:
            r2 = run_round2(r2_setup.estimated_votes, total_seats, bonus_fraction)
            result.round2 = r2

        return result

    def run(
        self,
        paris_scores: Dict[str, float],
        sector_scores: Dict[str, Dict[str, float]],
        inscrits_paris: int = 1_400_000,
        inscrits_par_secteur: Optional[Dict[str, int]] = None,
        participation: float = PARTICIPATION_DEFAUT,
        participation_par_secteur: Optional[Dict[str, float]] = None,
        interround_paris: Optional[InterRoundConfig] = None,
        interround_par_secteur: Optional[Dict[str, InterRoundConfig]] = None,
        mayor_candidates: Optional[List[MayorCandidate]] = None,
    ) -> ElectionResult:
        """Simulation complète des municipales parisiennes.

        Args:
            paris_scores: dict liste → % pour le Conseil de Paris.
            sector_scores: dict secteur → (dict liste → %) pour les arr.
            inscrits_paris: nombre d'inscrits à Paris.
            inscrits_par_secteur: dict secteur → inscrits (estimé si absent).
            participation: taux de participation global.
            participation_par_secteur: dict secteur → participation.
            interround_paris: config entre-tours Conseil de Paris.
            interround_par_secteur: dict secteur → config entre-tours.
            mayor_candidates: candidats au poste de maire.

        Returns:
            ElectionResult complet.
        """
        # --- Conseil de Paris ---
        paris_votes = self.scores_to_votes(paris_scores, inscrits_paris, participation)
        conseil = self.simulate_scrutin(
            name="Conseil de Paris",
            votes=paris_votes,
            total_seats=CONSEIL_PARIS_SEATS,
            bonus_fraction=CONSEIL_PARIS_BONUS_FRACTION,
            interround_config=interround_paris,
            inscrits=inscrits_paris,
            participation=participation,
        )

        # --- Conseils d'arrondissement ---
        arrondissements: Dict[str, ScrutinResult] = {}

        # Estimation des inscrits par secteur (proportionnel à la pop)
        if inscrits_par_secteur is None:
            total_arr_seats = sum(CONSEIL_ARRONDISSEMENT_SEATS.values())
            inscrits_par_secteur = {
                sect: round(inscrits_paris * seats / total_arr_seats)
                for sect, seats in CONSEIL_ARRONDISSEMENT_SEATS.items()
            }

        for secteur in SECTEURS:
            scores = sector_scores.get(secteur, paris_scores)
            seats = CONSEIL_ARRONDISSEMENT_SEATS.get(secteur, 0)
            if seats == 0:
                continue

            inscrits_s = inscrits_par_secteur.get(secteur, 50_000)
            part_s = (participation_par_secteur or {}).get(secteur, participation)
            ir_config = (interround_par_secteur or {}).get(secteur)

            s_votes = self.scores_to_votes(scores, inscrits_s, part_s)
            arr_result = self.simulate_scrutin(
                name=secteur,
                votes=s_votes,
                total_seats=seats,
                bonus_fraction=CONSEIL_ARRONDISSEMENT_BONUS_FRACTION,
                interround_config=ir_config,
                inscrits=inscrits_s,
                participation=part_s,
            )
            arrondissements[secteur] = arr_result

        # --- Élection du maire ---
        mayor_result = None
        if mayor_candidates and conseil.resolved:
            mayor_result = simulate_mayor_election(conseil.seats, mayor_candidates)

        return ElectionResult(
            conseil_paris=conseil,
            arrondissements=arrondissements,
            mayor=mayor_result,
        )
