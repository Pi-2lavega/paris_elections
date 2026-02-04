"""Moteur de correction brut → net (redressement des sondages).

Deux méthodes :
  - Multiplicative : ratio résultat/sondage
  - Additive : différence résultat - sondage

Calibration sur 4 élections historiques, pondération par récence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class CorrectionMethod(Enum):
    MULTIPLICATIVE = "multiplicative"
    ADDITIVE = "additive"


@dataclass
class CalibrationPoint:
    """Un point de calibration : sondage vs résultat pour une famille."""
    election: str
    family: str
    poll_score: float       # Score sondage (brut, en %)
    actual_score: float     # Score réel (en %)
    year: int = 2020


@dataclass
class CorrectionFactor:
    """Facteur de correction pour une famille politique."""
    family: str
    method: CorrectionMethod
    factor: float          # ratio (multiplicatif) ou delta (additif)
    std: float = 0.0       # écart-type du facteur
    n_points: int = 0
    confidence_low: float = 0.0
    confidence_high: float = 0.0


class RedressementModel:
    """Modèle de redressement brut → net.

    Calibré sur les élections historiques avec pondération par récence.
    """

    def __init__(
        self,
        method: CorrectionMethod = CorrectionMethod.MULTIPLICATIVE,
        half_life: float = 2.0,
        reference_year: int = 2026,
    ):
        """
        Args:
            method: méthode de correction.
            half_life: demi-vie en nombre d'élections pour la pondération.
            reference_year: année de référence (pour le calcul de la récence).
        """
        self.method = method
        self.half_life = half_life
        self.reference_year = reference_year
        self.calibration_data: List[CalibrationPoint] = []
        self.factors: Dict[str, CorrectionFactor] = {}

    def add_calibration_point(self, point: CalibrationPoint):
        """Ajoute un point de calibration."""
        self.calibration_data.append(point)

    def add_calibration_points(self, points: List[CalibrationPoint]):
        """Ajoute plusieurs points de calibration."""
        self.calibration_data.extend(points)

    def _weight(self, year: int) -> float:
        """Poids temporel basé sur la distance à l'année de référence."""
        distance = abs(self.reference_year - year)
        # Demi-vie en années (approximation : 1 élection ≈ 2-3 ans)
        years_half_life = self.half_life * 2.5
        return np.exp(-np.log(2) * distance / years_half_life)

    def calibrate(self):
        """Calibre les facteurs de correction à partir des données."""
        from collections import defaultdict

        by_family: Dict[str, List[Tuple[float, float, float]]] = defaultdict(list)
        # (poll_score, actual_score, weight)

        for pt in self.calibration_data:
            w = self._weight(pt.year)
            by_family[pt.family].append((pt.poll_score, pt.actual_score, w))

        self.factors.clear()

        for family, points in by_family.items():
            polls = np.array([p[0] for p in points])
            actuals = np.array([p[1] for p in points])
            weights = np.array([p[2] for p in points])
            weights /= weights.sum()

            if self.method == CorrectionMethod.MULTIPLICATIVE:
                # ratio = actual / poll (éviter division par 0)
                ratios = np.where(polls > 0.5, actuals / polls, 1.0)
                factor = float(np.average(ratios, weights=weights))
                std = float(np.sqrt(np.average((ratios - factor) ** 2, weights=weights)))
            else:
                # delta = actual - poll
                deltas = actuals - polls
                factor = float(np.average(deltas, weights=weights))
                std = float(np.sqrt(np.average((deltas - factor) ** 2, weights=weights)))

            self.factors[family] = CorrectionFactor(
                family=family,
                method=self.method,
                factor=factor,
                std=std,
                n_points=len(points),
                confidence_low=factor - 1.96 * std,
                confidence_high=factor + 1.96 * std,
            )

    def correct(
        self,
        scores_brut: Dict[str, float],
        family_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Applique la correction brut → net et renormalise.

        Args:
            scores_brut: dict liste → score brut (en %).
            family_mapping: dict liste → code famille (si None, clé = famille).

        Returns:
            dict liste → score corrigé (en %, somme = 100).
        """
        corrected = {}

        for liste, score in scores_brut.items():
            family = family_mapping.get(liste, liste) if family_mapping else liste
            cf = self.factors.get(family)

            if cf is None:
                corrected[liste] = score
                continue

            if self.method == CorrectionMethod.MULTIPLICATIVE:
                corrected[liste] = score * cf.factor
            else:
                corrected[liste] = score + cf.factor

        # Renormaliser à 100%
        total = sum(corrected.values())
        if total > 0:
            corrected = {k: v / total * 100 for k, v in corrected.items()}

        # Clamper les valeurs négatives
        corrected = {k: max(0.0, v) for k, v in corrected.items()}
        total = sum(corrected.values())
        if total > 0:
            corrected = {k: v / total * 100 for k, v in corrected.items()}

        return corrected

    def uncertainty_band(
        self,
        scores_brut: Dict[str, float],
        family_mapping: Optional[Dict[str, str]] = None,
        confidence: float = 0.95,
    ) -> Dict[str, Tuple[float, float, float]]:
        """Calcule les bandes d'incertitude (low, central, high).

        Args:
            scores_brut: scores bruts.
            family_mapping: mapping liste → famille.
            confidence: niveau de confiance (défaut 95%).

        Returns:
            dict liste → (low, central, high).
        """
        # Z-score for confidence interval (using approximation to avoid scipy dependency)
        # For 95% confidence: z ≈ 1.96
        z_table = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_table.get(confidence, 1.96)

        central = self.correct(scores_brut, family_mapping)
        bands = {}

        for liste, score in scores_brut.items():
            family = family_mapping.get(liste, liste) if family_mapping else liste
            cf = self.factors.get(family)

            if cf is None or cf.std == 0:
                bands[liste] = (central[liste], central[liste], central[liste])
                continue

            if self.method == CorrectionMethod.MULTIPLICATIVE:
                low = score * (cf.factor - z * cf.std)
                high = score * (cf.factor + z * cf.std)
            else:
                low = score + cf.factor - z * cf.std
                high = score + cf.factor + z * cf.std

            bands[liste] = (max(0.0, low), central[liste], max(0.0, high))

        return bands

    def summary(self) -> Dict[str, dict]:
        """Résumé des facteurs de correction."""
        return {
            family: {
                "method": cf.method.value,
                "factor": round(cf.factor, 4),
                "std": round(cf.std, 4),
                "n_points": cf.n_points,
                "ci_95": (round(cf.confidence_low, 4), round(cf.confidence_high, 4)),
            }
            for family, cf in self.factors.items()
        }
