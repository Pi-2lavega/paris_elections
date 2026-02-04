"""Diagramme hémicycle du Conseil de Paris.

Affiche la composition en sièges sous forme de demi-cercle,
avec le seuil de majorité à 82 sièges.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from paris_elections.config import (
    CONSEIL_PARIS_SEATS,
    MAYOR_ABSOLUTE_MAJORITY,
    POLITICAL_FAMILIES,
)


def _seat_positions(n_seats: int, n_rows: int = 8) -> List[Tuple[float, float]]:
    """Calcule les positions (x, y) de chaque siège en demi-cercle.

    Les sièges sont disposés en arcs concentriques de rayon croissant.
    """
    positions = []
    # Répartition des sièges par rangée (plus de sièges sur les rangées extérieures)
    seats_per_row = []
    remaining = n_seats
    for i in range(n_rows):
        row_seats = max(1, round(remaining / (n_rows - i)))
        seats_per_row.append(row_seats)
        remaining -= row_seats
    # Ajuster la dernière rangée
    seats_per_row[-1] += remaining

    r_min, r_max = 1.5, 4.0
    for row_idx, n_in_row in enumerate(seats_per_row):
        r = r_min + (r_max - r_min) * row_idx / max(1, n_rows - 1)
        for j in range(n_in_row):
            if n_in_row > 1:
                angle = np.pi * (j / (n_in_row - 1))
            else:
                angle = np.pi / 2
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            positions.append((x, y))

    return positions[:n_seats]


def plot_hemicycle(
    seats: Dict[str, int],
    title: str = "Conseil de Paris — 163 sièges",
    figsize: Tuple[int, int] = (12, 7),
    show_majority_line: bool = True,
    family_colors: Optional[Dict[str, str]] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """Dessine un diagramme hémicycle.

    Args:
        seats: dict liste → nombre de sièges.
        title: titre du graphique.
        figsize: taille de la figure.
        show_majority_line: afficher le seuil de majorité.
        family_colors: couleurs personnalisées (dict liste → couleur hex).
        ax: axes matplotlib (crée une figure si None).

    Returns:
        Figure matplotlib.
    """
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    total = sum(seats.values())
    positions = _seat_positions(total)

    # Trier les listes de gauche à droite (par convention)
    order = ["EXG", "LFI", "PCF", "PS", "EELV", "DVG", "MDM", "REN", "LR", "DVD", "RN", "REC", "EXD", "DIV"]
    sorted_lists = sorted(
        seats.keys(),
        key=lambda x: order.index(x) if x in order else len(order),
    )

    # Couleurs par défaut
    if family_colors is None:
        family_colors = {}
    colors = {}
    for liste in sorted_lists:
        if liste in family_colors:
            colors[liste] = family_colors[liste]
        elif liste in POLITICAL_FAMILIES:
            colors[liste] = POLITICAL_FAMILIES[liste].color
        else:
            colors[liste] = "#999999"

    # Placer les sièges
    idx = 0
    for liste in sorted_lists:
        n = seats.get(liste, 0)
        color = colors.get(liste, "#999999")
        for _ in range(n):
            if idx < len(positions):
                x, y = positions[idx]
                ax.scatter(x, y, c=color, s=60, edgecolors="white", linewidth=0.5, zorder=3)
                idx += 1

    # Ligne de majorité
    if show_majority_line:
        ax.axhline(y=0, color="black", linewidth=1.5, zorder=1)
        ax.text(0, -0.3, f"Majorité : {MAYOR_ABSOLUTE_MAJORITY} sièges",
                ha="center", va="top", fontsize=10, style="italic")

    # Légende
    legend_patches = []
    for liste in sorted_lists:
        n = seats.get(liste, 0)
        if n > 0:
            label = f"{liste} ({n})"
            if liste in POLITICAL_FAMILIES:
                label = f"{POLITICAL_FAMILIES[liste].label} ({n})"
            legend_patches.append(mpatches.Patch(color=colors[liste], label=label))

    ax.legend(
        handles=legend_patches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=min(4, len(legend_patches)),
        fontsize=8,
    )

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlim(-5, 5)
    ax.set_ylim(-0.8, 5)
    ax.set_aspect("equal")
    ax.axis("off")

    fig.tight_layout()
    return fig
