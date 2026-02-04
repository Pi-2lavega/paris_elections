"""Cartes Folium — choroplèthes par secteur.

Visualisations :
  - Vainqueur par secteur
  - Marge de victoire
  - Participation
  - Score d'une liste
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import folium
from folium import plugins

from paris_elections.config import SECTEURS, POLITICAL_FAMILIES

# Coordonnées centre de Paris
PARIS_CENTER = [48.8566, 2.3522]

# GeoJSON des arrondissements (simplifié — coordonnées approximatives des centres)
# En production, utiliser un vrai GeoJSON depuis data.gouv.fr
SECTOR_CENTERS: Dict[str, tuple] = {
    "Paris Centre": (48.8606, 2.3480),
    "5e":  (48.8440, 2.3480),
    "6e":  (48.8500, 2.3320),
    "7e":  (48.8560, 2.3120),
    "8e":  (48.8740, 2.3120),
    "9e":  (48.8770, 2.3370),
    "10e": (48.8760, 2.3600),
    "11e": (48.8580, 2.3800),
    "12e": (48.8400, 2.4000),
    "13e": (48.8300, 2.3600),
    "14e": (48.8300, 2.3260),
    "15e": (48.8400, 2.2920),
    "16e": (48.8630, 2.2700),
    "17e": (48.8900, 2.3100),
    "18e": (48.8920, 2.3440),
    "19e": (48.8850, 2.3820),
    "20e": (48.8650, 2.3980),
}


def _get_color(liste: str) -> str:
    """Retourne la couleur associée à une liste/famille."""
    if liste in POLITICAL_FAMILIES:
        return POLITICAL_FAMILIES[liste].color
    return "#999999"


def map_winners(
    winners: Dict[str, str],
    title: str = "Vainqueur par secteur",
) -> folium.Map:
    """Carte avec le vainqueur par secteur (marqueurs colorés).

    Args:
        winners: dict secteur → liste gagnante.
        title: titre de la carte (non affiché directement par Folium).

    Returns:
        Carte Folium.
    """
    m = folium.Map(location=PARIS_CENTER, zoom_start=12, tiles="cartodbpositron")

    for secteur, center in SECTOR_CENTERS.items():
        winner = winners.get(secteur, "?")
        color = _get_color(winner)

        folium.CircleMarker(
            location=center,
            radius=15,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=f"<b>{secteur}</b><br>Vainqueur : {winner}",
        ).add_to(m)

        folium.Marker(
            location=center,
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px; text-align:center;">{secteur}</div>',
            ),
        ).add_to(m)

    return m


def map_scores(
    scores: Dict[str, float],
    liste: str,
    cmap: str = "YlOrRd",
    title: str = "",
) -> folium.Map:
    """Carte des scores d'une liste par secteur.

    Args:
        scores: dict secteur → score (en %).
        liste: nom de la liste (pour le titre).
        cmap: palette de couleurs.
        title: titre optionnel.

    Returns:
        Carte Folium.
    """
    import matplotlib.pyplot as plt
    from matplotlib import cm
    import matplotlib.colors as mcolors

    m = folium.Map(location=PARIS_CENTER, zoom_start=12, tiles="cartodbpositron")

    # Normaliser les scores
    vals = list(scores.values())
    vmin, vmax = min(vals) if vals else 0, max(vals) if vals else 1
    if vmax == vmin:
        vmax = vmin + 1
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colormap = cm.get_cmap(cmap)

    for secteur, center in SECTOR_CENTERS.items():
        score = scores.get(secteur, 0)
        rgba = colormap(norm(score))
        hex_color = mcolors.to_hex(rgba)

        folium.CircleMarker(
            location=center,
            radius=20,
            color=hex_color,
            fill=True,
            fill_color=hex_color,
            fill_opacity=0.7,
            popup=f"<b>{secteur}</b><br>{liste} : {score:.1f}%",
        ).add_to(m)

    return m


def map_participation(
    participation: Dict[str, float],
) -> folium.Map:
    """Carte de la participation par secteur.

    Args:
        participation: dict secteur → taux (0-1).

    Returns:
        Carte Folium.
    """
    # Convertir en pourcentage
    scores_pct = {s: p * 100 for s, p in participation.items()}
    return map_scores(scores_pct, "Participation", cmap="Blues", title="Participation")


def map_margin(
    margins: Dict[str, float],
) -> folium.Map:
    """Carte de la marge de victoire par secteur.

    Args:
        margins: dict secteur → marge (T1 - T2 en points).

    Returns:
        Carte Folium.
    """
    return map_scores(margins, "Marge", cmap="RdYlGn", title="Marge de victoire")
