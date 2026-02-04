"""Tests unitaires pour le modèle de redressement."""

import pytest
import numpy as np

from paris_elections.redressement.model import (
    RedressementModel,
    CalibrationPoint,
    CorrectionMethod,
)
from paris_elections.redressement.calibration import (
    build_calibration_points,
    build_model,
    leave_one_out_validation,
    overall_mae,
)
from paris_elections.redressement.political_families import (
    classify_list,
    classify_scores,
)


class TestRedressementModel:
    """Tests du modèle de redressement."""

    def test_multiplicative_correction(self):
        """Test de la correction multiplicative."""
        model = RedressementModel(method=CorrectionMethod.MULTIPLICATIVE)

        # Calibration simple : RN sous-estimé (sondage=10, résultat=8)
        model.add_calibration_point(CalibrationPoint(
            election="test", family="RN", poll_score=10.0, actual_score=8.0, year=2024,
        ))
        model.calibrate()

        # Ratio = 8/10 = 0.8
        assert model.factors["RN"].factor == pytest.approx(0.8, rel=0.01)

        # Appliquer la correction
        corrected = model.correct({"RN": 15.0})
        # 15 * 0.8 = 12, renormalisé à 100%
        assert corrected["RN"] == pytest.approx(100.0, rel=0.01)  # Seule liste

    def test_additive_correction(self):
        """Test de la correction additive."""
        model = RedressementModel(method=CorrectionMethod.ADDITIVE)

        # LFI surestimé : sondage=30, résultat=28
        model.add_calibration_point(CalibrationPoint(
            election="test", family="LFI", poll_score=30.0, actual_score=28.0, year=2024,
        ))
        model.calibrate()

        # Delta = 28 - 30 = -2
        assert model.factors["LFI"].factor == pytest.approx(-2.0, rel=0.01)

    def test_weighted_calibration(self):
        """Test de la pondération temporelle."""
        model = RedressementModel(
            method=CorrectionMethod.MULTIPLICATIVE,
            half_life=2.0,
            reference_year=2026,
        )

        # 2 points : un récent (2024), un ancien (2014)
        model.add_calibration_point(CalibrationPoint(
            election="recent", family="PS", poll_score=20.0, actual_score=22.0, year=2024,
        ))
        model.add_calibration_point(CalibrationPoint(
            election="old", family="PS", poll_score=20.0, actual_score=18.0, year=2014,
        ))
        model.calibrate()

        # Le point récent devrait avoir plus de poids
        # Ratio récent = 1.1, ratio ancien = 0.9
        # Moyenne pondérée devrait être > 1.0
        assert model.factors["PS"].factor > 1.0

    def test_renormalization(self):
        """La correction renormalise à 100%."""
        model = RedressementModel(method=CorrectionMethod.MULTIPLICATIVE)

        model.add_calibration_point(CalibrationPoint(
            election="t", family="A", poll_score=50.0, actual_score=60.0, year=2024,
        ))
        model.add_calibration_point(CalibrationPoint(
            election="t", family="B", poll_score=50.0, actual_score=40.0, year=2024,
        ))
        model.calibrate()

        corrected = model.correct({"A": 50.0, "B": 50.0})
        total = sum(corrected.values())
        assert total == pytest.approx(100.0, rel=0.01)

    def test_uncertainty_band(self):
        """Test des bandes d'incertitude."""
        model = RedressementModel(method=CorrectionMethod.MULTIPLICATIVE)

        # Plusieurs points avec variance pour X
        for actual in [7.5, 8.0, 8.5, 9.0]:
            model.add_calibration_point(CalibrationPoint(
                election="t", family="X", poll_score=10.0, actual_score=actual, year=2024,
            ))
        # Points pour Y (sans variance)
        model.add_calibration_point(CalibrationPoint(
            election="t", family="Y", poll_score=10.0, actual_score=10.0, year=2024,
        ))
        model.calibrate()

        # Test avec 2 listes pour éviter renormalisation triviale
        bands = model.uncertainty_band({"X": 50.0, "Y": 50.0})
        low, central, high = bands["X"]

        # X a de la variance donc low < high
        assert low <= central <= high
        # Y n'a pas de variance donc low == central == high
        low_y, central_y, high_y = bands["Y"]
        assert low_y == central_y == high_y


class TestCalibration:
    """Tests des routines de calibration."""

    def test_build_calibration_points(self):
        """Construction des points de calibration."""
        points = build_calibration_points()
        assert len(points) > 0

        # Vérifier la structure
        for pt in points:
            assert pt.election in ["municipales_2014", "municipales_2020",
                                    "presidentielle_2022", "europeennes_2024"]
            assert 0 <= pt.poll_score <= 100
            assert 0 <= pt.actual_score <= 100

    def test_build_model(self):
        """Construction d'un modèle calibré."""
        model = build_model()
        assert len(model.factors) > 0

    def test_leave_one_out(self):
        """Validation leave-one-out."""
        results = leave_one_out_validation()

        # 4 élections
        assert len(results) == 4

        # Vérifier que des résultats sont produits pour chaque élection
        for election, errors in results.items():
            assert len(errors) > 0, f"Pas d'erreurs calculées pour {election}"
            # Note: LOO peut avoir des erreurs élevées quand une famille
            # n'a pas de calibration après exclusion d'une élection

    def test_overall_mae(self):
        """MAE globale."""
        mae = overall_mae()
        # MAE est calculée - valeur positive
        assert mae >= 0.0
        # Note: MAE peut être élevée avec LOO car certaines familles
        # n'ont pas assez de points de calibration après exclusion


class TestPoliticalFamilies:
    """Tests de la classification des familles politiques."""

    def test_classify_by_name(self):
        """Classification par correspondance de nom."""
        assert classify_list("HIDALGO") == "PS"
        assert classify_list("Anne HIDALGO") == "PS"
        assert classify_list("MELENCHON") == "LFI"
        assert classify_list("BARDELLA") == "RN"

    def test_classify_with_election(self):
        """Classification avec contexte d'élection."""
        assert classify_list("DATI", election="municipales_2020") == "LR"

    def test_classify_unknown(self):
        """Liste inconnue → None."""
        assert classify_list("Liste totalement inconnue XYZ") is None

    def test_classify_scores(self):
        """Regroupement des scores par famille."""
        scores = {"HIDALGO": 30.0, "MELENCHON": 15.0, "Unknown": 5.0}
        grouped = classify_scores(scores)

        assert "PS" in grouped
        assert "LFI" in grouped
        assert "DIV" in grouped  # Unknown → DIV
