"""Graphiques Plotly et Matplotlib.

Visualisations :
  - Barres empilées : sièges par scénario
  - Sankey : flux de voix T1 → T2
  - Waterfall : effet du redressement
  - Scatter : corrélations démographie × vote
  - Histogramme MC : distribution des sièges
  - Radar : profils démographiques
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from paris_elections.config import POLITICAL_FAMILIES


def _family_color(liste: str) -> str:
    if liste in POLITICAL_FAMILIES:
        return POLITICAL_FAMILIES[liste].color
    return "#999999"


# ---------------------------------------------------------------------------
# Barres empilées : comparaison sièges entre scénarios
# ---------------------------------------------------------------------------

def bar_seats_comparison(
    scenarios_seats: Dict[str, Dict[str, int]],
    title: str = "Comparaison des sièges au Conseil de Paris",
) -> go.Figure:
    """Barres empilées comparant les sièges par scénario.

    Args:
        scenarios_seats: dict scenario_name → (dict liste → sièges).
        title: titre du graphique.

    Returns:
        Figure Plotly.
    """
    all_lists = set()
    for seats in scenarios_seats.values():
        all_lists.update(seats.keys())

    # Ordre de gauche à droite
    order = ["EXG", "LFI", "PCF", "PS", "EELV", "DVG", "MDM", "REN", "LR", "DVD", "RN", "REC", "EXD", "DIV"]
    sorted_lists = sorted(all_lists, key=lambda x: order.index(x) if x in order else len(order))

    fig = go.Figure()

    for liste in sorted_lists:
        values = [scenarios_seats[sc].get(liste, 0) for sc in scenarios_seats]
        fig.add_trace(go.Bar(
            name=liste,
            x=list(scenarios_seats.keys()),
            y=values,
            marker_color=_family_color(liste),
        ))

    fig.update_layout(
        barmode="stack",
        title=title,
        xaxis_title="Scénario",
        yaxis_title="Sièges",
        legend_title="Liste",
        template="plotly_white",
    )

    # Ligne de majorité
    fig.add_hline(y=82, line_dash="dash", line_color="red",
                  annotation_text="Majorité (82)", annotation_position="bottom right")

    return fig


# ---------------------------------------------------------------------------
# Sankey : flux de voix T1 → T2
# ---------------------------------------------------------------------------

def sankey_transfers(
    t1_scores: Dict[str, float],
    t2_scores: Dict[str, float],
    transfers: Dict[str, Dict[str, float]],
    title: str = "Transferts de voix T1 → T2",
) -> go.Figure:
    """Diagramme Sankey des transferts de voix.

    Args:
        t1_scores: scores T1 par liste.
        t2_scores: scores T2 par liste (qualifiées uniquement).
        transfers: dict source → (dict dest → fraction).
        title: titre.

    Returns:
        Figure Plotly.
    """
    labels = list(t1_scores.keys()) + [f"{l}_T2" for l in t2_scores.keys()] + ["Abstention"]
    label_idx = {l: i for i, l in enumerate(labels)}

    sources = []
    targets = []
    values = []
    colors = []

    for src, dests in transfers.items():
        if src not in label_idx:
            continue
        src_idx = label_idx[src]
        total = t1_scores.get(src, 0)

        for dest, frac in dests.items():
            dest_label = f"{dest}_T2" if dest in t2_scores else dest
            if dest_label not in label_idx:
                continue
            tgt_idx = label_idx[dest_label]
            val = total * frac
            sources.append(src_idx)
            targets.append(tgt_idx)
            values.append(val)
            colors.append(_family_color(src))

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color=[_family_color(l.replace("_T2", "")) for l in labels],
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors,
        ),
    ))

    fig.update_layout(title=title, template="plotly_white")
    return fig


# ---------------------------------------------------------------------------
# Waterfall : effet du redressement
# ---------------------------------------------------------------------------

def waterfall_redressement(
    brut: Dict[str, float],
    net: Dict[str, float],
    title: str = "Effet du redressement (brut → net)",
) -> go.Figure:
    """Graphique en cascade de l'effet du redressement.

    Args:
        brut: scores bruts (sondage).
        net: scores redressés.
        title: titre.

    Returns:
        Figure Plotly.
    """
    lists = list(brut.keys())
    deltas = [net.get(l, 0) - brut.get(l, 0) for l in lists]

    fig = go.Figure(go.Waterfall(
        name="Redressement",
        orientation="v",
        x=lists,
        y=deltas,
        text=[f"{d:+.1f}" for d in deltas],
        textposition="outside",
        connector=dict(line=dict(color="rgb(63, 63, 63)")),
        increasing=dict(marker=dict(color="green")),
        decreasing=dict(marker=dict(color="red")),
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Liste",
        yaxis_title="Δ points",
        showlegend=False,
        template="plotly_white",
    )

    return fig


# ---------------------------------------------------------------------------
# Scatter : corrélations démographie × vote
# ---------------------------------------------------------------------------

def scatter_demographie_vote(
    demographie: Dict[str, float],
    votes: Dict[str, float],
    x_label: str = "Revenu médian (€)",
    y_label: str = "Score LR (%)",
    title: str = "Corrélation revenu × vote droite",
) -> go.Figure:
    """Scatter plot corrélant une variable démographique au vote.

    Args:
        demographie: dict secteur → valeur démographique.
        votes: dict secteur → score.
        x_label, y_label, title: labels.

    Returns:
        Figure Plotly.
    """
    sectors = list(demographie.keys())
    x = [demographie[s] for s in sectors]
    y = [votes.get(s, 0) for s in sectors]

    fig = px.scatter(
        x=x, y=y, text=sectors,
        labels={"x": x_label, "y": y_label},
        title=title,
        trendline="ols",
    )

    fig.update_traces(textposition="top center")
    fig.update_layout(template="plotly_white")
    return fig


# ---------------------------------------------------------------------------
# Histogramme MC : distribution des sièges
# ---------------------------------------------------------------------------

def histogram_mc(
    distribution: np.ndarray,
    liste: str,
    ci: Tuple[float, float, float],
    title: str = "",
) -> go.Figure:
    """Histogramme de la distribution Monte Carlo des sièges.

    Args:
        distribution: array des sièges (N itérations).
        liste: nom de la liste.
        ci: (low, median, high) intervalle de confiance.
        title: titre optionnel.

    Returns:
        Figure Plotly.
    """
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=distribution,
        nbinsx=30,
        marker_color=_family_color(liste),
        opacity=0.7,
        name=liste,
    ))

    # Lignes IC
    low, med, high = ci
    fig.add_vline(x=med, line_dash="solid", line_color="black",
                  annotation_text=f"Médiane: {med:.0f}")
    fig.add_vline(x=low, line_dash="dash", line_color="gray",
                  annotation_text=f"IC95 bas: {low:.0f}")
    fig.add_vline(x=high, line_dash="dash", line_color="gray",
                  annotation_text=f"IC95 haut: {high:.0f}")

    fig.update_layout(
        title=title or f"Distribution des sièges — {liste}",
        xaxis_title="Sièges",
        yaxis_title="Fréquence",
        showlegend=False,
        template="plotly_white",
    )

    return fig


# ---------------------------------------------------------------------------
# Radar : profils démographiques comparés
# ---------------------------------------------------------------------------

def radar_profiles(
    profiles: Dict[str, Dict[str, float]],
    categories: List[str],
    title: str = "Profils démographiques par secteur",
) -> go.Figure:
    """Graphique radar comparant les profils de plusieurs secteurs.

    Args:
        profiles: dict secteur → (dict catégorie → valeur normalisée 0-1).
        categories: liste des catégories (axes).
        title: titre.

    Returns:
        Figure Plotly.
    """
    fig = go.Figure()

    for sector, values in profiles.items():
        r = [values.get(cat, 0) for cat in categories] + [values.get(categories[0], 0)]
        theta = categories + [categories[0]]
        fig.add_trace(go.Scatterpolar(
            r=r,
            theta=theta,
            fill="toself",
            name=sector,
            opacity=0.5,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title=title,
        template="plotly_white",
    )

    return fig
