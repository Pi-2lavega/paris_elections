"""Routines de calibration du modèle de redressement.

Construction du dataset de calibration à partir des élections historiques
(moyennes des derniers sondages vs résultats Paris).
Validation croisée leave-one-out.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from paris_elections.redressement.model import (
    CalibrationPoint,
    CorrectionMethod,
    RedressementModel,
)


# ---------------------------------------------------------------------------
# Données de calibration intégrées (Paris uniquement)
#
# Format : (family, poll_score, actual_score)
# poll_score = moyenne des derniers sondages avant le scrutin
# actual_score = résultat officiel à Paris
# ---------------------------------------------------------------------------

# Municipales 2014 (Paris) — approximations
CALIBRATION_MUNICIPALES_2014: List[Tuple[str, float, float]] = [
    ("PS",   34.0, 34.4),
    ("LR",   22.0, 22.7),
    ("EELV", 10.0,  8.9),
    ("REN",   4.0,  3.0),  # UDI/Centre à l'époque
    ("LFI",   5.0,  6.2),  # Front de Gauche
    ("RN",    7.0,  6.3),
]

# Municipales 2020 (Paris T1)
CALIBRATION_MUNICIPALES_2020: List[Tuple[str, float, float]] = [
    ("PS",   30.0, 29.3),
    ("LR",   22.0, 22.7),
    ("EELV", 12.0, 10.8),
    ("REN",  17.0, 13.7),
    ("LFI",   3.5,  3.2),
    ("PCF",   3.0,  2.8),
    ("RN",    2.0,  1.5),
]

# Présidentielle 2022 T1 (Paris)
CALIBRATION_PRESIDENTIELLE_2022: List[Tuple[str, float, float]] = [
    ("LFI",  28.0, 30.1),
    ("REN",  30.0, 35.3),
    ("EELV",  5.0,  5.8),
    ("PS",    2.0,  2.2),
    ("PCF",   3.0,  2.8),
    ("LR",    5.0,  4.1),
    ("RN",   10.0,  5.1),
    ("REC",   8.0,  5.5),
]

# Européennes 2024 (Paris)
CALIBRATION_EUROPEENNES_2024: List[Tuple[str, float, float]] = [
    ("PS",   16.0, 22.6),  # Glucksmann
    ("REN",  16.0, 17.2),
    ("LFI",  10.0, 12.0),
    ("EELV",  7.0,  7.8),
    ("LR",    8.0,  6.6),
    ("RN",   15.0,  7.4),
    ("REC",   5.0,  3.8),
]

ALL_CALIBRATION = {
    "municipales_2014": (2014, CALIBRATION_MUNICIPALES_2014),
    "municipales_2020": (2020, CALIBRATION_MUNICIPALES_2020),
    "presidentielle_2022": (2022, CALIBRATION_PRESIDENTIELLE_2022),
    "europeennes_2024": (2024, CALIBRATION_EUROPEENNES_2024),
}


def build_calibration_points(
    elections: Optional[List[str]] = None,
) -> List[CalibrationPoint]:
    """Construit la liste des points de calibration.

    Args:
        elections: sous-ensemble d'élections à utiliser (None = toutes).

    Returns:
        Liste de CalibrationPoint.
    """
    points = []
    keys = elections or list(ALL_CALIBRATION.keys())

    for key in keys:
        if key not in ALL_CALIBRATION:
            continue
        year, data = ALL_CALIBRATION[key]
        for family, poll, actual in data:
            points.append(CalibrationPoint(
                election=key,
                family=family,
                poll_score=poll,
                actual_score=actual,
                year=year,
            ))

    return points


def build_model(
    method: CorrectionMethod = CorrectionMethod.MULTIPLICATIVE,
    elections: Optional[List[str]] = None,
    half_life: float = 2.0,
) -> RedressementModel:
    """Construit et calibre un modèle de redressement.

    Args:
        method: méthode de correction.
        elections: élections à utiliser pour la calibration.
        half_life: demi-vie (en nombre d'élections).

    Returns:
        RedressementModel calibré.
    """
    model = RedressementModel(method=method, half_life=half_life)
    points = build_calibration_points(elections)
    model.add_calibration_points(points)
    model.calibrate()
    return model


def leave_one_out_validation(
    method: CorrectionMethod = CorrectionMethod.MULTIPLICATIVE,
    half_life: float = 2.0,
) -> Dict[str, Dict[str, float]]:
    """Validation croisée leave-one-out.

    Pour chaque élection, calibre sur les N-1 autres puis prédit l'élection
    omise. Retourne l'erreur (MAE) par famille et par élection.

    Returns:
        dict élection → dict famille → erreur absolue (en points).
    """
    results = {}
    all_keys = list(ALL_CALIBRATION.keys())

    for test_key in all_keys:
        train_keys = [k for k in all_keys if k != test_key]
        model = build_model(method=method, elections=train_keys, half_life=half_life)

        year, test_data = ALL_CALIBRATION[test_key]
        errors = {}

        for family, poll, actual in test_data:
            corrected = model.correct({family: poll})
            predicted = corrected.get(family, poll)
            errors[family] = abs(predicted - actual)

        results[test_key] = errors

    return results


def overall_mae(
    method: CorrectionMethod = CorrectionMethod.MULTIPLICATIVE,
    half_life: float = 2.0,
) -> float:
    """MAE globale de la validation leave-one-out."""
    loo = leave_one_out_validation(method, half_life)
    all_errors = []
    for errors in loo.values():
        all_errors.extend(errors.values())
    return float(np.mean(all_errors)) if all_errors else 0.0
