"""Définition, sérialisation et comparaison de scénarios électoraux."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from paris_elections.config import (
    SECTEURS,
    PARTICIPATION_DEFAUT,
    COALITION_GAUCHE,
    COALITION_CENTRE,
    COALITION_DROITE,
)
from paris_elections.engine.interround import InterRoundConfig
from paris_elections.engine.simulation import ElectionResult, ElectionSimulator


@dataclass
class Scenario:
    """Scénario électoral complet.

    Contient les hypothèses (scores, participation, alliances) et peut être
    simulé pour produire un ElectionResult.
    """
    name: str
    description: str = ""
    source: str = "manuel"  # "sondage", "manuel", "montecarlo"

    # Scores au T1 (en %) — Conseil de Paris
    paris_scores: Dict[str, float] = field(default_factory=dict)

    # Scores par secteur (si absent, on utilise paris_scores)
    sector_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Participation
    participation: float = PARTICIPATION_DEFAUT
    participation_par_secteur: Dict[str, float] = field(default_factory=dict)

    # Inscrits
    inscrits_paris: int = 1_400_000
    inscrits_par_secteur: Dict[str, int] = field(default_factory=dict)

    # Config entre-tours
    interround_paris: Optional[Dict] = None
    interround_par_secteur: Dict[str, Dict] = field(default_factory=dict)

    # Métadonnées
    metadata: Dict[str, Any] = field(default_factory=dict)

    def variant(self, **kwargs) -> Scenario:
        """Crée une variante de ce scénario avec des modifications.

        Utile pour l'analyse de sensibilité.

        Args:
            **kwargs: attributs à modifier.

        Returns:
            Nouveau Scenario modifié.
        """
        new = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new, key):
                setattr(new, key, value)
        if "name" not in kwargs:
            new.name = f"{self.name} (variante)"
        return new

    def simulate(self) -> ElectionResult:
        """Exécute la simulation pour ce scénario.

        Returns:
            ElectionResult complet.
        """
        sim = ElectionSimulator()

        ir_paris = None
        if self.interround_paris:
            ir_paris = InterRoundConfig(**self.interround_paris)

        ir_secteurs = {}
        for s, cfg in self.interround_par_secteur.items():
            ir_secteurs[s] = InterRoundConfig(**cfg)

        return sim.run(
            paris_scores=self.paris_scores,
            sector_scores=self.sector_scores,
            inscrits_paris=self.inscrits_paris,
            inscrits_par_secteur=self.inscrits_par_secteur or None,
            participation=self.participation,
            participation_par_secteur=self.participation_par_secteur or None,
            interround_paris=ir_paris,
            interround_par_secteur=ir_secteurs or None,
        )

    def to_json(self, path: Optional[str] = None) -> str:
        """Sérialise le scénario en JSON.

        Args:
            path: chemin du fichier (optionnel).

        Returns:
            Chaîne JSON.
        """
        data = asdict(self)
        s = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        if path:
            Path(path).write_text(s)
        return s

    @classmethod
    def from_json(cls, json_str: Optional[str] = None, path: Optional[str] = None) -> Scenario:
        """Désérialise un scénario depuis JSON.

        Args:
            json_str: chaîne JSON.
            path: chemin du fichier.

        Returns:
            Scenario.
        """
        if path:
            json_str = Path(path).read_text()
        if json_str is None:
            raise ValueError("json_str ou path requis.")
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ScenarioComparator:
    """Comparaison multi-scénarios."""
    scenarios: List[Scenario] = field(default_factory=list)
    results: Dict[str, ElectionResult] = field(default_factory=dict)

    def add(self, scenario: Scenario):
        self.scenarios.append(scenario)

    def run_all(self) -> Dict[str, ElectionResult]:
        """Simule tous les scénarios."""
        self.results.clear()
        for sc in self.scenarios:
            self.results[sc.name] = sc.simulate()
        return self.results

    def seats_table(self) -> Dict[str, Dict[str, int]]:
        """Tableau comparatif des sièges au Conseil de Paris."""
        return {
            name: result.total_seats_conseil
            for name, result in self.results.items()
        }

    def coalition_summary(self) -> Dict[str, Dict[str, int]]:
        """Résumé par coalition pour chaque scénario."""
        from paris_elections.config import MAYOR_ABSOLUTE_MAJORITY

        summary = {}
        for name, result in self.results.items():
            seats = result.total_seats_conseil
            gauche = sum(seats.get(l, 0) for l in seats if l in COALITION_GAUCHE)
            centre = sum(seats.get(l, 0) for l in seats if l in COALITION_CENTRE)
            droite = sum(seats.get(l, 0) for l in seats if l in COALITION_DROITE)
            summary[name] = {
                "Gauche": gauche,
                "Centre": centre,
                "Droite": droite,
                "Majorité (82)": max(gauche, centre, droite) >= MAYOR_ABSOLUTE_MAJORITY,
            }
        return summary


# ---------------------------------------------------------------------------
# Scénarios prédéfinis
# ---------------------------------------------------------------------------

def scenario_gauche_unie() -> Scenario:
    """Scénario : gauche unie derrière une liste unique PS-EELV-LFI-PCF."""
    return Scenario(
        name="Gauche unie",
        description="Liste unique gauche PS-EELV-LFI-PCF, face à REN, LR, RN séparés",
        paris_scores={
            "Gauche unie": 38.0,
            "REN": 20.0,
            "LR": 18.0,
            "RN": 10.0,
            "REC": 5.0,
            "DIV": 9.0,
        },
        participation=0.48,
    )


def scenario_droite_unie() -> Scenario:
    """Scénario : droite unie LR + Renaissance."""
    return Scenario(
        name="Droite unie",
        description="Alliance LR-REN, gauche fragmentée",
        paris_scores={
            "PS": 18.0,
            "LFI": 12.0,
            "EELV": 8.0,
            "PCF": 3.0,
            "LR-REN": 32.0,
            "RN": 10.0,
            "REC": 5.0,
            "DIV": 12.0,
        },
        participation=0.46,
    )


def scenario_fragmentation() -> Scenario:
    """Scénario : fragmentation maximale — aucune alliance."""
    return Scenario(
        name="Fragmentation maximale",
        description="Toutes les forces politiques présentent des listes séparées",
        paris_scores={
            "PS": 16.0,
            "LFI": 14.0,
            "EELV": 8.0,
            "PCF": 4.0,
            "REN": 18.0,
            "MDM": 3.0,
            "LR": 15.0,
            "RN": 9.0,
            "REC": 5.0,
            "EXG": 2.0,
            "DIV": 6.0,
        },
        participation=0.42,
    )
