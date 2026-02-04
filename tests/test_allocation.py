"""Tests unitaires pour l'algorithme D'Hondt et l'allocation des sièges."""

import pytest
from paris_elections.engine.allocation import (
    plus_forte_moyenne,
    allocate_with_bonus,
    compute_quotient_table,
)


class TestPlusForteMoyenne:
    """Tests de la répartition proportionnelle D'Hondt."""

    def test_simple_case(self):
        """Cas simple avec 2 listes."""
        votes = {"A": 600, "B": 400}
        seats = plus_forte_moyenne(votes, 10)
        # D'Hondt : A devrait avoir 6, B devrait avoir 4
        assert seats["A"] == 6
        assert seats["B"] == 4

    def test_three_lists(self):
        """Cas avec 3 listes."""
        votes = {"A": 100_000, "B": 80_000, "C": 20_000}
        seats = plus_forte_moyenne(votes, 8)
        # Vérifie la somme
        assert sum(seats.values()) == 8

    def test_with_threshold(self):
        """Test du seuil d'éligibilité."""
        votes = {"A": 600, "B": 350, "C": 50}  # C < 5%
        seats = plus_forte_moyenne(votes, 10, threshold_pct=0.05)
        # C ne devrait pas avoir de sièges
        assert seats["C"] == 0
        assert sum(seats.values()) == 10

    def test_single_list(self):
        """Une seule liste obtient tous les sièges."""
        votes = {"A": 1000}
        seats = plus_forte_moyenne(votes, 5)
        assert seats["A"] == 5

    def test_zero_seats(self):
        """Aucun siège à attribuer."""
        votes = {"A": 500, "B": 500}
        seats = plus_forte_moyenne(votes, 0)
        assert seats["A"] == 0
        assert seats["B"] == 0

    def test_empty_votes(self):
        """Aucune voix."""
        votes = {"A": 0, "B": 0}
        seats = plus_forte_moyenne(votes, 10)
        # Comportement défini : répartition entre listes existantes
        assert sum(seats.values()) <= 10


class TestAllocateWithBonus:
    """Tests de l'allocation avec prime majoritaire."""

    def test_bonus_25_pct(self):
        """Prime de 25% (Conseil de Paris)."""
        votes = {"A": 400, "B": 350, "C": 250}
        seats = allocate_with_bonus(votes, 100, bonus_fraction=0.25)
        # A gagne → reçoit 25 sièges de prime
        # Puis proportionnelle sur 75 sièges
        assert sum(seats.values()) == 100
        assert seats["A"] >= 25  # Prime garantie

    def test_bonus_50_pct(self):
        """Prime de 50% (conseils d'arrondissement)."""
        votes = {"X": 600, "Y": 400}
        seats = allocate_with_bonus(votes, 40, bonus_fraction=0.50)
        # X reçoit 20 sièges de prime puis participe aux 20 restants
        assert sum(seats.values()) == 40
        assert seats["X"] >= 20

    def test_specified_winner(self):
        """Winner explicitement spécifié."""
        votes = {"A": 100, "B": 200}
        seats = allocate_with_bonus(votes, 10, bonus_fraction=0.30, winner="A")
        # A reçoit la prime même s'il n'est pas en tête
        assert seats["A"] >= 3

    def test_threshold_proportional(self):
        """Seuil sur la partie proportionnelle."""
        votes = {"A": 600, "B": 350, "C": 40, "D": 10}
        seats = allocate_with_bonus(votes, 100, bonus_fraction=0.25, threshold_pct=0.05)
        # C et D sous 5% ne participent pas à la proportionnelle
        assert sum(seats.values()) == 100


class TestQuotientTable:
    """Tests de la table des quotients."""

    def test_table_order(self):
        """La table est triée par quotient décroissant."""
        votes = {"A": 120, "B": 80}
        table = compute_quotient_table(votes, max_divisor=5)
        # Premier quotient = 120/1 = 120
        assert table[0] == ("A", 1, 120.0)
        # Vérifier l'ordre
        for i in range(len(table) - 1):
            assert table[i][2] >= table[i + 1][2]


class TestHistoricalValidation:
    """Validation sur des cas historiques connus."""

    def test_municipales_2020_paris_approximation(self):
        """Approximation des résultats 2020 (ancien système).

        Note : Ce test utilise des valeurs simplifiées pour valider
        la logique de l'algorithme, pas les résultats exacts de 2020.
        """
        # Simulation simplifiée avec 3 listes principales
        votes = {
            "Hidalgo": 29300,
            "Dati": 22700,
            "Buzyn": 13700,
        }
        # Avec prime 50% sur 163 sièges (simplification)
        seats = allocate_with_bonus(votes, 163, bonus_fraction=0.25)

        # Hidalgo gagne → devrait avoir majorité confortable
        assert seats["Hidalgo"] > seats["Dati"]
        assert seats["Hidalgo"] > seats["Buzyn"]
        assert sum(seats.values()) == 163
