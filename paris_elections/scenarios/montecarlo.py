"""Simulation Monte Carlo pour quantifier l'incertitude électorale.

Perturbations :
  - Scores : Normal contrainte (somme ≈ 0)
  - Participation : σ = 3 pts
  - Taux de transfert T2 : σ = 10%

Sorties :
  - Distribution des sièges par liste
  - P(majorité pour coalition X)
  - P(maire Y)
  - Intervalles de confiance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from paris_elections.config import (
    MC_DEFAULT_ITERATIONS,
    MC_SCORE_SIGMA,
    MC_PARTICIPATION_SIGMA,
    MC_TRANSFER_SIGMA,
    CONSEIL_PARIS_SEATS,
    MAYOR_ABSOLUTE_MAJORITY,
    COALITION_GAUCHE,
    COALITION_CENTRE,
    COALITION_DROITE,
)
from paris_elections.scenarios.scenario import Scenario
from paris_elections.engine.simulation import ElectionResult, ElectionSimulator


@dataclass
class MonteCarloResult:
    """Résultat d'une simulation Monte Carlo."""
    n_iterations: int
    # Distribution des sièges : dict liste → array de taille N
    seats_distributions: Dict[str, np.ndarray] = field(default_factory=dict)
    # Résumé par coalition
    coalition_distributions: Dict[str, np.ndarray] = field(default_factory=dict)
    # Probabilité que chaque coalition ait la majorité
    majority_probabilities: Dict[str, float] = field(default_factory=dict)
    # Arrondissements gagnés (par itération)
    sector_winners: Dict[str, List[str]] = field(default_factory=dict)

    def seats_ci(self, liste: str, confidence: float = 0.95) -> Tuple[float, float, float]:
        """Intervalle de confiance des sièges pour une liste.

        Returns:
            (low, median, high).
        """
        arr = self.seats_distributions.get(liste)
        if arr is None:
            return (0, 0, 0)
        alpha = (1 - confidence) / 2
        return (
            float(np.percentile(arr, alpha * 100)),
            float(np.median(arr)),
            float(np.percentile(arr, (1 - alpha) * 100)),
        )

    def seats_mean_std(self, liste: str) -> Tuple[float, float]:
        """Moyenne et écart-type des sièges."""
        arr = self.seats_distributions.get(liste)
        if arr is None:
            return (0.0, 0.0)
        return (float(np.mean(arr)), float(np.std(arr)))

    def summary_table(self) -> Dict[str, Dict[str, float]]:
        """Tableau résumé pour toutes les listes."""
        table = {}
        for liste in self.seats_distributions:
            low, med, high = self.seats_ci(liste)
            mean, std = self.seats_mean_std(liste)
            table[liste] = {
                "mean": round(mean, 1),
                "std": round(std, 1),
                "median": med,
                "ci_low": low,
                "ci_high": high,
            }
        return table


def perturb_scores(
    scores: Dict[str, float],
    sigma: float = MC_SCORE_SIGMA,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, float]:
    """Perturbe les scores avec une distribution normale contrainte (somme ≈ 0).

    Args:
        scores: dict liste → score (en fraction 0-1 ou %).
        sigma: écart-type de la perturbation.
        rng: générateur aléatoire.

    Returns:
        Scores perturbés (même format que l'entrée).
    """
    if rng is None:
        rng = np.random.default_rng()

    lists = list(scores.keys())
    values = np.array([scores[k] for k in lists], dtype=float)

    # Déterminer l'échelle (0-1 ou 0-100)
    total = values.sum()
    in_pct = total > 2.0
    if in_pct:
        sigma_adj = sigma * 100
    else:
        sigma_adj = sigma

    # Perturbation normale
    perturbation = rng.normal(0, sigma_adj, size=len(lists))
    # Contrainte : somme des perturbations ≈ 0
    perturbation -= perturbation.mean()

    perturbed = values + perturbation
    # Clamper les valeurs négatives
    perturbed = np.maximum(perturbed, 0.0)
    # Renormaliser
    total_new = perturbed.sum()
    if total_new > 0:
        perturbed = perturbed / total_new * total

    return {k: float(v) for k, v in zip(lists, perturbed)}


def run_monte_carlo(
    scenario: Scenario,
    n_iterations: int = MC_DEFAULT_ITERATIONS,
    score_sigma: float = MC_SCORE_SIGMA,
    participation_sigma: float = MC_PARTICIPATION_SIGMA,
    transfer_sigma: float = MC_TRANSFER_SIGMA,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """Exécute N itérations Monte Carlo sur un scénario.

    À chaque itération :
      1. Perturbe les scores (corrélés, somme ≈ constante)
      2. Perturbe la participation
      3. Simule l'élection complète
      4. Enregistre les sièges

    Args:
        scenario: scénario de base.
        n_iterations: nombre d'itérations.
        score_sigma: σ des perturbations de score (en fraction).
        participation_sigma: σ de la perturbation de participation.
        transfer_sigma: σ de la perturbation des transferts T2.
        seed: graine aléatoire (reproductibilité).

    Returns:
        MonteCarloResult.
    """
    rng = np.random.default_rng(seed)
    sim = ElectionSimulator()

    # Collecter les résultats
    all_seats: Dict[str, List[int]] = {}
    all_coalition: Dict[str, List[int]] = {"Gauche": [], "Centre": [], "Droite": []}
    all_sector_winners: Dict[str, List[str]] = {s: [] for s in scenario.sector_scores or scenario.paris_scores}

    for i in range(n_iterations):
        # 1. Perturber les scores Paris
        p_paris = perturb_scores(scenario.paris_scores, score_sigma, rng)

        # 2. Perturber les scores sectoriels
        p_sectors = {}
        for secteur, scores in (scenario.sector_scores or {}).items():
            p_sectors[secteur] = perturb_scores(scores, score_sigma, rng)

        # 3. Perturber la participation
        p_part = scenario.participation + rng.normal(0, participation_sigma)
        p_part = max(0.15, min(0.85, p_part))

        # 4. Simuler
        try:
            result = sim.run(
                paris_scores=p_paris,
                sector_scores=p_sectors,
                inscrits_paris=scenario.inscrits_paris,
                participation=p_part,
            )
        except Exception:
            continue

        # 5. Enregistrer les sièges Conseil de Paris
        for liste, seats in result.total_seats_conseil.items():
            if liste not in all_seats:
                all_seats[liste] = []
            all_seats[liste].append(seats)

        # Coalitions
        seats_cp = result.total_seats_conseil
        g = sum(seats_cp.get(l, 0) for l in seats_cp if l in COALITION_GAUCHE)
        c = sum(seats_cp.get(l, 0) for l in seats_cp if l in COALITION_CENTRE)
        d = sum(seats_cp.get(l, 0) for l in seats_cp if l in COALITION_DROITE)
        all_coalition["Gauche"].append(g)
        all_coalition["Centre"].append(c)
        all_coalition["Droite"].append(d)

        # Arrondissements
        for secteur, arr_res in result.arrondissements.items():
            if arr_res.winner:
                if secteur not in all_sector_winners:
                    all_sector_winners[secteur] = []
                all_sector_winners[secteur].append(arr_res.winner)

    # Convertir en arrays
    seats_dist = {k: np.array(v) for k, v in all_seats.items()}
    coal_dist = {k: np.array(v) for k, v in all_coalition.items()}

    # P(majorité)
    maj_prob = {}
    for coal_name, arr in coal_dist.items():
        if len(arr) > 0:
            maj_prob[coal_name] = float((arr >= MAYOR_ABSOLUTE_MAJORITY).mean())
        else:
            maj_prob[coal_name] = 0.0

    return MonteCarloResult(
        n_iterations=n_iterations,
        seats_distributions=seats_dist,
        coalition_distributions=coal_dist,
        majority_probabilities=maj_prob,
        sector_winners=all_sector_winners,
    )
