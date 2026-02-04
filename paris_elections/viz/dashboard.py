"""Dashboard interactif ipywidgets.

Interface principale de simulation avec sliders pour :
  - Scores par liste
  - Participation
  - Affichage temps réel des résultats
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

try:
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    WIDGETS_AVAILABLE = True
except ImportError:
    WIDGETS_AVAILABLE = False

from paris_elections.config import (
    POLITICAL_FAMILIES,
    FAMILY_CODES,
    PARTICIPATION_DEFAUT,
    CONSEIL_PARIS_SEATS,
    MAYOR_ABSOLUTE_MAJORITY,
)
from paris_elections.engine.simulation import ElectionSimulator
from paris_elections.viz.hemicycle import plot_hemicycle


class ElectionDashboard:
    """Dashboard interactif pour la simulation électorale."""

    def __init__(
        self,
        initial_scores: Optional[Dict[str, float]] = None,
        families: Optional[List[str]] = None,
    ):
        """
        Args:
            initial_scores: scores initiaux par famille (en %).
            families: familles politiques à afficher.
        """
        if not WIDGETS_AVAILABLE:
            raise ImportError("ipywidgets requis pour le dashboard. Installer avec: pip install ipywidgets")

        self.families = families or ["PS", "LFI", "EELV", "PCF", "REN", "LR", "RN", "REC", "DIV"]
        self.simulator = ElectionSimulator()

        # Scores par défaut
        default_scores = {
            "PS": 18.0, "LFI": 14.0, "EELV": 8.0, "PCF": 4.0,
            "REN": 18.0, "LR": 16.0, "RN": 8.0, "REC": 5.0, "DIV": 9.0,
        }
        self.current_scores = initial_scores or default_scores

        # Widgets
        self._build_widgets()

    def _build_widgets(self):
        """Construit les widgets du dashboard."""
        # Sliders pour les scores
        self.score_sliders = {}
        for family in self.families:
            color = POLITICAL_FAMILIES.get(family, POLITICAL_FAMILIES["DIV"]).color
            label = POLITICAL_FAMILIES.get(family, POLITICAL_FAMILIES["DIV"]).label

            slider = widgets.FloatSlider(
                value=self.current_scores.get(family, 5.0),
                min=0.0,
                max=50.0,
                step=0.5,
                description=family,
                style={"description_width": "60px"},
                layout=widgets.Layout(width="400px"),
            )
            slider.observe(self._on_score_change, names="value")
            self.score_sliders[family] = slider

        # Slider participation
        self.participation_slider = widgets.FloatSlider(
            value=PARTICIPATION_DEFAUT * 100,
            min=20.0,
            max=80.0,
            step=1.0,
            description="Participation %",
            style={"description_width": "100px"},
            layout=widgets.Layout(width="400px"),
        )
        self.participation_slider.observe(self._on_score_change, names="value")

        # Affichage du total (doit faire 100%)
        self.total_label = widgets.HTML(value="<b>Total : 100.0%</b>")

        # Zone de résultats
        self.output = widgets.Output()

        # Bouton simulation
        self.run_button = widgets.Button(
            description="Simuler",
            button_style="primary",
            icon="play",
        )
        self.run_button.on_click(self._on_run)

        # Bouton normaliser
        self.normalize_button = widgets.Button(
            description="Normaliser à 100%",
            button_style="info",
            icon="balance-scale",
        )
        self.normalize_button.on_click(self._on_normalize)

    def _get_scores(self) -> Dict[str, float]:
        """Récupère les scores des sliders."""
        return {f: self.score_sliders[f].value for f in self.families}

    def _update_total(self):
        """Met à jour l'affichage du total."""
        total = sum(self.score_sliders[f].value for f in self.families)
        color = "green" if 99.5 <= total <= 100.5 else "red"
        self.total_label.value = f"<b style='color:{color}'>Total : {total:.1f}%</b>"

    def _on_score_change(self, change):
        """Callback lors du changement d'un score."""
        self._update_total()

    def _on_normalize(self, _):
        """Normalise les scores à 100%."""
        scores = self._get_scores()
        total = sum(scores.values())
        if total > 0:
            factor = 100.0 / total
            for f in self.families:
                self.score_sliders[f].value = round(scores[f] * factor, 1)
        self._update_total()

    def _on_run(self, _):
        """Exécute la simulation."""
        import matplotlib.pyplot as plt

        scores = self._get_scores()
        participation = self.participation_slider.value / 100.0

        # Simuler
        result = self.simulator.run(
            paris_scores=scores,
            sector_scores={},  # Utiliser les scores Paris pour tous les secteurs
            participation=participation,
        )

        # Afficher les résultats
        with self.output:
            clear_output(wait=True)

            seats = result.total_seats_conseil
            total_seats = sum(seats.values())

            # Résumé textuel
            print(f"=== Résultats Conseil de Paris ({total_seats} sièges) ===\n")

            for family in sorted(seats.keys(), key=lambda x: seats[x], reverse=True):
                n = seats[family]
                pct = n / total_seats * 100 if total_seats > 0 else 0
                bar = "█" * (n // 3)
                print(f"{family:6} : {n:3} sièges ({pct:5.1f}%) {bar}")

            # Majorité ?
            max_family = max(seats, key=seats.get) if seats else None
            max_seats = seats.get(max_family, 0) if max_family else 0
            print(f"\n🏆 Liste en tête : {max_family} ({max_seats} sièges)")
            if max_seats >= MAYOR_ABSOLUTE_MAJORITY:
                print(f"✅ Majorité absolue atteinte ({MAYOR_ABSOLUTE_MAJORITY} requis)")
            else:
                deficit = MAYOR_ABSOLUTE_MAJORITY - max_seats
                print(f"❌ Pas de majorité absolue ({deficit} sièges manquants)")

            # Hémicycle
            fig = plot_hemicycle(seats, figsize=(10, 6))
            plt.show()

    def display(self):
        """Affiche le dashboard."""
        # Layout
        sliders_box = widgets.VBox(list(self.score_sliders.values()))
        controls_box = widgets.HBox([
            self.participation_slider,
            self.normalize_button,
            self.run_button,
        ])

        header = widgets.HTML(
            "<h2>🗳️ Simulation Municipales Paris 2026</h2>"
            "<p>Ajustez les scores et cliquez sur Simuler.</p>"
        )

        layout = widgets.VBox([
            header,
            widgets.HBox([sliders_box, self.total_label]),
            controls_box,
            self.output,
        ])

        display(layout)
        self._update_total()


def create_dashboard(**kwargs) -> ElectionDashboard:
    """Factory function pour créer un dashboard.

    Usage dans un notebook :
        from paris_elections.viz.dashboard import create_dashboard
        dashboard = create_dashboard()
        dashboard.display()
    """
    return ElectionDashboard(**kwargs)
