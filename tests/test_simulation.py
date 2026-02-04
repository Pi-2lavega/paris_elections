"""Tests unitaires pour le simulateur électoral."""

import pytest
from paris_elections.engine.simulation import ElectionSimulator, ElectionResult
from paris_elections.engine.round1 import run_round1, Round1Result
from paris_elections.engine.round2 import run_round2
from paris_elections.engine.interround import InterRoundConfig, Fusion, apply_interround
from paris_elections.config import (
    CONSEIL_PARIS_SEATS,
    CONSEIL_PARIS_BONUS_FRACTION,
    SEUIL_VICTOIRE_T1,
)


class TestRound1:
    """Tests du premier tour."""

    def test_resolution_t1_majority(self):
        """Liste avec >50% gagne au T1."""
        votes = {"A": 5500, "B": 2500, "C": 2000}
        result = run_round1(votes, 100, 0.25)

        assert result.resolved is True
        assert result.winner == "A"
        assert result.seats is not None
        assert sum(result.seats.values()) == 100

    def test_no_resolution_t1(self):
        """Pas de majorité → T2 nécessaire."""
        votes = {"A": 4500, "B": 3500, "C": 2000}
        result = run_round1(votes, 100, 0.25)

        assert result.resolved is False
        assert result.winner is None
        assert result.seats is None

    def test_qualification_thresholds(self):
        """Test des seuils de qualification."""
        # A: 45%, B: 35%, C: 8%, D: 7%, E: 5%
        votes = {"A": 4500, "B": 3500, "C": 800, "D": 700, "E": 500}
        result = run_round1(votes, 100, 0.25)

        assert "A" in result.qualified  # ≥10%
        assert "B" in result.qualified  # ≥10%
        assert "C" in result.fusionable  # 5-10%
        assert "D" in result.fusionable  # 5-10%
        assert "E" in result.fusionable  # = 5%


class TestRound2:
    """Tests du second tour."""

    def test_plurality_wins(self):
        """La liste en tête au T2 reçoit la prime."""
        votes = {"A": 5500, "B": 4500}
        result = run_round2(votes, 100, 0.25)

        assert result.winner == "A"
        assert sum(result.seats.values()) == 100
        assert result.seats["A"] > result.seats["B"]


class TestInterRound:
    """Tests de la logique entre-deux-tours."""

    def test_fusion(self):
        """Test d'une fusion de liste."""
        round1_votes = {"A": 4500, "B": 3500, "C": 800, "D": 1200}
        qualified = ["A", "B"]
        fusionable = ["C", "D"]
        eliminated = []

        config = InterRoundConfig(
            fusions=[Fusion(absorbed="C", into="A", transfer_rate=0.85)]
        )

        setup = apply_interround(
            round1_votes, qualified, fusionable, eliminated,
            config, inscrits=10000, participation_t1=1.0,
        )

        assert "A" in setup.lists_in_round2
        assert "B" in setup.lists_in_round2
        # C a fusionné avec A, D n'a pas fusionné (ni qualifié)
        assert "C" not in setup.lists_in_round2

    def test_triangulaire_detection(self):
        """Détection d'une triangulaire."""
        round1_votes = {"A": 4000, "B": 3500, "C": 2500}
        qualified = ["A", "B", "C"]
        fusionable = []
        eliminated = []

        config = InterRoundConfig()
        setup = apply_interround(
            round1_votes, qualified, fusionable, eliminated,
            config, inscrits=10000, participation_t1=1.0,
        )

        assert setup.is_triangulaire is True
        assert len(setup.lists_in_round2) == 3


class TestElectionSimulator:
    """Tests du simulateur complet."""

    def test_full_simulation_resolved_t1(self):
        """Simulation complète avec résolution au T1."""
        sim = ElectionSimulator()

        # Liste dominante à >50%
        paris_scores = {"A": 55.0, "B": 30.0, "C": 15.0}

        result = sim.run(
            paris_scores=paris_scores,
            sector_scores={},
            participation=0.50,
        )

        assert result.conseil_paris.resolved is True
        assert result.conseil_paris.winner == "A"
        assert sum(result.conseil_paris.seats.values()) == CONSEIL_PARIS_SEATS

    def test_full_simulation_t2(self):
        """Simulation avec T2."""
        sim = ElectionSimulator()

        # Pas de majorité au T1
        paris_scores = {"A": 35.0, "B": 30.0, "C": 20.0, "D": 15.0}

        result = sim.run(
            paris_scores=paris_scores,
            sector_scores={},
            participation=0.45,
        )

        assert result.conseil_paris.resolved is True
        assert result.conseil_paris.round2 is not None
        assert sum(result.conseil_paris.seats.values()) == CONSEIL_PARIS_SEATS

    def test_arrondissements_simulated(self):
        """Les conseils d'arrondissement sont simulés."""
        sim = ElectionSimulator()

        paris_scores = {"A": 55.0, "B": 45.0}

        result = sim.run(
            paris_scores=paris_scores,
            sector_scores={},
            participation=0.45,
        )

        # 17 secteurs simulés
        assert len(result.arrondissements) == 17

        for name, arr_result in result.arrondissements.items():
            assert arr_result.resolved is True
            assert sum(arr_result.seats.values()) == arr_result.total_seats

    def test_scores_to_votes_normalization(self):
        """Conversion scores → votes avec normalisation."""
        sim = ElectionSimulator()

        # Scores en pourcentage (ne font pas 100%)
        scores = {"A": 40.0, "B": 30.0, "C": 20.0}  # Total = 90%
        votes = sim.scores_to_votes(scores, inscrits=100000, participation=0.50)

        # Total des votes = 50000
        total = sum(votes.values())
        assert total == 50000

    def test_scores_to_votes_fraction(self):
        """Conversion depuis des fractions (0-1)."""
        sim = ElectionSimulator()

        scores = {"A": 0.40, "B": 0.35, "C": 0.25}
        votes = sim.scores_to_votes(scores, inscrits=100000, participation=0.60)

        total = sum(votes.values())
        assert total == 60000


class TestHistoricalValidation:
    """Validation sur des données historiques."""

    def test_seats_sum_conseil_paris(self):
        """Le total des sièges du Conseil de Paris est toujours 163."""
        sim = ElectionSimulator()

        # Plusieurs configurations
        configs = [
            {"A": 60.0, "B": 40.0},
            {"A": 35.0, "B": 30.0, "C": 20.0, "D": 15.0},
            {"A": 25.0, "B": 25.0, "C": 25.0, "D": 25.0},
        ]

        for scores in configs:
            result = sim.run(paris_scores=scores, sector_scores={})
            total = sum(result.conseil_paris.seats.values())
            assert total == CONSEIL_PARIS_SEATS, f"Expected {CONSEIL_PARIS_SEATS}, got {total}"
