"""
Streamlit Frontend — Simulation Municipales Paris 2026
=======================================================
UI moderne et épurée
"""

import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import pandas as pd
import numpy as np
from streamlit_echarts import st_echarts
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from paris_elections.engine.round1 import run_round1
from paris_elections.engine.round2 import run_round2
from paris_elections.engine.allocation import allocate_with_bonus
from paris_elections.config import (
    CONSEIL_PARIS_SEATS,
    CONSEIL_PARIS_BONUS_FRACTION,
    MAYOR_ABSOLUTE_MAJORITY,
    get_transfer_rate,
)


# =============================================================================
# MONTE CARLO SIMULATION
# =============================================================================

def perturb_scores_ui(scores: dict, sigma: float, rng) -> dict:
    """Perturbe les scores avec distribution normale contrainte."""
    lists = list(scores.keys())
    values = np.array([scores[k] for k in lists], dtype=float)

    # Perturbation normale
    perturbation = rng.normal(0, sigma, size=len(lists))
    # Contrainte : somme des perturbations ≈ 0
    perturbation -= perturbation.mean()

    perturbed = values + perturbation
    # Clamper les valeurs négatives
    perturbed = np.maximum(perturbed, 0.0)
    # Renormaliser à la somme originale
    total = values.sum()
    total_new = perturbed.sum()
    if total_new > 0:
        perturbed = perturbed / total_new * total

    return {k: float(v) for k, v in zip(lists, perturbed)}


def run_monte_carlo_ui(
    scores: dict,
    n_iterations: int,
    sigma: float,
    seed: int = None
) -> dict:
    """Monte Carlo simplifié pour l'UI.

    Returns:
        dict avec distributions de sièges et statistiques.
    """
    rng = np.random.default_rng(seed)

    # Collecter les résultats
    all_seats = {liste: [] for liste in scores}

    for _ in range(n_iterations):
        # 1. Perturber les scores
        p_scores = perturb_scores_ui(scores, sigma, rng)

        # 2. Convertir en votes (hypothèse : 1M d'inscrits, 50% participation)
        votes = {k: int(v * 10000) for k, v in p_scores.items()}

        # 3. Déterminer le vainqueur
        winner = max(votes, key=votes.get)

        # 4. Allocation D'Hondt avec prime 25%
        seats = allocate_with_bonus(
            votes,
            CONSEIL_PARIS_SEATS,
            CONSEIL_PARIS_BONUS_FRACTION,
            winner,
            threshold_pct=0.05
        )

        # 5. Enregistrer
        for liste in scores:
            all_seats[liste].append(seats.get(liste, 0))

    # Calculer statistiques
    results = {}
    for liste, seat_list in all_seats.items():
        arr = np.array(seat_list)
        results[liste] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "median": float(np.median(arr)),
            "ci_low": float(np.percentile(arr, 2.5)),
            "ci_high": float(np.percentile(arr, 97.5)),
            "distribution": arr.tolist(),
        }

    # Probabilité de majorité
    maj_count = 0
    for i in range(n_iterations):
        max_seats = max(all_seats[l][i] for l in all_seats)
        if max_seats >= MAYOR_ABSOLUTE_MAJORITY:
            maj_count += 1

    results["_meta"] = {
        "n_iterations": n_iterations,
        "p_majority": maj_count / n_iterations if n_iterations > 0 else 0,
    }

    return results


# =============================================================================
# EXPORT PDF
# =============================================================================

import base64
from datetime import datetime
import io

def generate_pdf_report(seats: dict, familles: dict, r1_result=None, mc_results=None) -> bytes:
    """Génère un rapport PDF simple en HTML converti."""

    # Trier par sièges
    sorted_seats = sorted(seats.items(), key=lambda x: -x[1])
    winner = sorted_seats[0][0]
    winner_seats = sorted_seats[0][1]
    has_majority = winner_seats >= MAYOR_ABSOLUTE_MAJORITY

    # Calcul par bloc
    blocs_seats = {"Gauche": 0, "Centre": 0, "Droite": 0, "Ext. Droite": 0}
    for liste, n in seats.items():
        bloc = get_bloc(familles.get(liste, "DIV"))
        if bloc in blocs_seats:
            blocs_seats[bloc] += n

    # Date du rapport
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # Construction du HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; color: #333; }}
            h1 {{ color: #1a1a2e; border-bottom: 3px solid #6366f1; padding-bottom: 10px; }}
            h2 {{ color: #4a4a6a; margin-top: 30px; }}
            .winner-box {{ background: #f0f0ff; border-left: 5px solid #6366f1; padding: 20px; margin: 20px 0; }}
            .winner-name {{ font-size: 24px; font-weight: bold; color: #1a1a2e; }}
            .winner-seats {{ font-size: 36px; font-weight: bold; color: #6366f1; }}
            .majority {{ color: #22c55e; font-weight: bold; }}
            .no-majority {{ color: #ef4444; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background: #f5f5f5; font-weight: bold; }}
            tr:nth-child(even) {{ background: #fafafa; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h1>🗳️ Simulation Municipales Paris 2026</h1>
        <p>Rapport généré le {now}</p>

        <div class="winner-box">
            <div class="winner-name">{winner}</div>
            <div class="winner-seats">{winner_seats} / {CONSEIL_PARIS_SEATS} sièges</div>
            <div class="{'majority' if has_majority else 'no-majority'}">
                {'✓ Majorité absolue atteinte' if has_majority else '✗ Pas de majorité absolue'}
            </div>
        </div>

        <h2>Répartition des sièges</h2>
        <table>
            <tr><th>Liste</th><th>Famille</th><th>Sièges</th><th>%</th></tr>
    """

    for liste, n in sorted_seats:
        if n > 0:
            pct = n / CONSEIL_PARIS_SEATS * 100
            famille = familles.get(liste, "DIV")
            html += f"<tr><td>{liste}</td><td>{famille}</td><td>{n}</td><td>{pct:.1f}%</td></tr>"

    html += """
        </table>

        <h2>Analyse par bloc</h2>
        <table>
            <tr><th>Bloc</th><th>Sièges</th><th>%</th></tr>
    """

    for bloc, n in blocs_seats.items():
        if n > 0:
            pct = n / CONSEIL_PARIS_SEATS * 100
            html += f"<tr><td>{bloc}</td><td>{n}</td><td>{pct:.1f}%</td></tr>"

    html += "</table>"

    # Coalitions
    html += """
        <h2>Coalitions possibles</h2>
        <table>
            <tr><th>Coalition</th><th>Sièges</th><th>Majorité ?</th></tr>
    """

    coalitions = [
        ("Gauche", blocs_seats["Gauche"]),
        ("Gauche + Centre", blocs_seats["Gauche"] + blocs_seats["Centre"]),
        ("Droite + Centre", blocs_seats["Droite"] + blocs_seats["Centre"]),
    ]

    for name, total in coalitions:
        status = "✓ Oui" if total >= MAYOR_ABSOLUTE_MAJORITY else "✗ Non"
        html += f"<tr><td>{name}</td><td>{total}</td><td>{status}</td></tr>"

    html += """
        </table>

        <h2>Paramètres de simulation</h2>
        <ul>
            <li>Conseil de Paris : 163 sièges</li>
            <li>Prime majoritaire : 25% (41 sièges)</li>
            <li>Seuil de représentation : 5%</li>
            <li>Majorité absolue : 82 sièges</li>
        </ul>
    """

    # Monte Carlo si disponible
    if mc_results and "_meta" in mc_results:
        meta = mc_results["_meta"]
        p_maj = meta.get("p_majority", 0) * 100
        html += f"""
        <h2>Simulation Monte Carlo</h2>
        <p>Basé sur {meta.get('n_iterations', 0):,} itérations</p>
        <p><strong>Probabilité de majorité absolue :</strong> {p_maj:.1f}%</p>
        <table>
            <tr><th>Liste</th><th>Moyenne</th><th>IC 95%</th></tr>
        """
        for liste, stats in mc_results.items():
            if liste != "_meta":
                html += f"<tr><td>{liste}</td><td>{stats['mean']:.1f}</td><td>[{stats['ci_low']:.0f} - {stats['ci_high']:.0f}]</td></tr>"
        html += "</table>"

    html += f"""
        <div class="footer">
            <p>Généré par le Simulateur Municipales Paris 2026</p>
            <p>Algorithme D'Hondt · Prime majoritaire 25% · Données indicatives</p>
        </div>
    </body>
    </html>
    """

    return html.encode('utf-8')


def get_download_link(html_bytes: bytes, filename: str) -> str:
    """Génère un lien de téléchargement pour le HTML."""
    b64 = base64.b64encode(html_bytes).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">📥 Télécharger le rapport</a>'


# =============================================================================
# PAGE CONFIG & CUSTOM CSS
# =============================================================================

st.set_page_config(
    page_title="Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS - Fira.money inspired dark theme
st.markdown("""
<style>
    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* CSS Variables - Fira.money palette */
    :root {
        --bg-base: #0a0a0a;
        --bg-card: #0f0f0f;
        --bg-elevated: #141414;
        --border-subtle: #1a1a1a;
        --border-muted: #2a2a2a;
        --text-primary: #ffffff;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;
        --accent-orange: #f97316;
        --accent-green: #22c55e;
        --accent-blue: #3b82f6;
        --accent-red: #ef4444;
    }

    /* Global */
    .stApp {
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        background: var(--bg-base) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}

    /* Main container */
    .main .block-container {
        max-width: 1200px;
        padding: 2rem 1rem;
    }

    /* Tabs styling - Fira style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-card);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid var(--border-subtle);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        font-size: 14px;
        color: var(--text-muted);
        background: transparent;
    }

    .stTabs [aria-selected="true"] {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-muted);
    }

    /* Cards - Fira style */
    .fira-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 20px;
    }

    .fira-card-inner {
        background: var(--bg-elevated);
        border: 1px solid var(--border-muted);
        border-radius: 8px;
        padding: 16px;
    }

    /* Section headers - Fira style */
    .section-header {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: var(--text-muted);
        margin-bottom: 12px;
    }

    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 16px;
    }

    .section-title span {
        color: var(--accent-orange);
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-success { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
    .badge-warning { background: rgba(234, 179, 8, 0.15); color: #facc15; }
    .badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .badge-info { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .badge-orange { background: rgba(249, 115, 22, 0.15); color: #fb923c; }

    /* Button styling - Fira style */
    .stButton > button {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-muted) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        border-color: var(--accent-orange) !important;
        background: var(--bg-elevated) !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--accent-orange) !important;
        border-color: var(--accent-orange) !important;
    }

    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
    }

    /* Input styling - Fira style */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-elevated) !important;
        border: 2px solid var(--border-muted) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-orange) !important;
        box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.2) !important;
    }

    .stSelectbox > div > div {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-muted) !important;
        border-radius: 8px !important;
    }

    /* Slider - Fira style */
    .stSlider > div > div > div > div {
        background: var(--accent-orange) !important;
    }

    /* Expander - Fira style */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        color: var(--text-secondary) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* Coalition cards */
    .coalition-success {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.25);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        color: #4ade80;
        font-weight: 500;
    }

    /* Analysis rows */
    .analysis-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--text-secondary);
    }

    .analysis-value {
        font-weight: 600;
        color: var(--text-primary);
    }

    .analysis-pct {
        color: var(--text-muted);
        font-weight: 400;
    }

    /* Metric display - Fira style */
    .metric-display {
        text-align: center;
    }

    .metric-label {
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
    }

    .metric-value.orange { color: var(--accent-orange); }
    .metric-value.green { color: var(--accent-green); }
    .metric-value.blue { color: var(--accent-blue); }

    /* Data table styling */
    .stDataFrame {
        background: var(--bg-card) !important;
        border-radius: 8px !important;
    }

    /* Toggle styling */
    .stCheckbox label span {
        color: var(--text-secondary) !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# COULEURS POLITIQUES
# =============================================================================

COLORS = {
    "EXG": "#8B0000", "LFI": "#CC2443", "PCF": "#DD0000", "PS": "#FF6B6B",
    "EELV": "#2ECC71", "DVG": "#FFC0CB", "REN": "#F1C40F", "MDM": "#FF9900",
    "UDI": "#00BFFF", "LR": "#3498DB", "DVD": "#74B4E8", "RN": "#1A1A2E",
    "REC": "#2C3E50", "EXD": "#404040", "DIV": "#95A5A6",
}

BLOCS = {
    "Gauche": ["PS", "LFI", "PCF", "EELV", "DVG", "EXG"],
    "Centre": ["REN", "MDM", "UDI"],
    "Droite": ["LR", "DVD"],
    "Ext. Droite": ["RN", "REC", "EXD"],
}

def get_color(famille):
    return COLORS.get(famille, "#95A5A6")

def get_bloc(famille):
    for bloc, familles in BLOCS.items():
        if famille in familles:
            return bloc
    return "Autre"


# =============================================================================
# CARTE PARIS - COORDONNÉES ARRONDISSEMENTS
# =============================================================================

# Centres approximatifs des arrondissements de Paris pour affichage simplifié
ARRONDISSEMENTS_COORDS = {
    "1er": (48.8607, 2.3417),
    "2e": (48.8679, 2.3418),
    "3e": (48.8643, 2.3597),
    "4e": (48.8541, 2.3573),
    "5e": (48.8462, 2.3502),
    "6e": (48.8498, 2.3326),
    "7e": (48.8566, 2.3150),
    "8e": (48.8744, 2.3106),
    "9e": (48.8769, 2.3379),
    "10e": (48.8761, 2.3607),
    "11e": (48.8596, 2.3781),
    "12e": (48.8412, 2.3876),
    "13e": (48.8322, 2.3561),
    "14e": (48.8331, 2.3264),
    "15e": (48.8421, 2.2929),
    "16e": (48.8637, 2.2769),
    "17e": (48.8872, 2.3055),
    "18e": (48.8925, 2.3444),
    "19e": (48.8871, 2.3822),
    "20e": (48.8638, 2.3985),
}

# Paris Centre = 1er + 2e + 3e + 4e
SECTEURS_2026 = {
    "Paris Centre": ["1er", "2e", "3e", "4e"],
    "5e": ["5e"],
    "6e": ["6e"],
    "7e": ["7e"],
    "8e": ["8e"],
    "9e": ["9e"],
    "10e": ["10e"],
    "11e": ["11e"],
    "12e": ["12e"],
    "13e": ["13e"],
    "14e": ["14e"],
    "15e": ["15e"],
    "16e": ["16e"],
    "17e": ["17e"],
    "18e": ["18e"],
    "19e": ["19e"],
    "20e": ["20e"],
}


def create_paris_map(seats_by_sector: dict = None, familles: dict = None) -> folium.Map:
    """Crée une carte de Paris avec les résultats par arrondissement."""
    # Centre de Paris
    m = folium.Map(
        location=[48.8566, 2.3522],
        zoom_start=12,
        tiles="CartoDB dark_matter"
    )

    # Si pas de données, afficher les arrondissements vides
    if not seats_by_sector:
        for arr, coords in ARRONDISSEMENTS_COORDS.items():
            folium.CircleMarker(
                location=coords,
                radius=15,
                color="white",
                fill=True,
                fill_color="#95A5A6",
                fill_opacity=0.6,
                popup=arr
            ).add_to(m)
        return m

    # Avec données : colorer selon le vainqueur
    for arr, coords in ARRONDISSEMENTS_COORDS.items():
        # Trouver le secteur correspondant
        secteur = None
        for s, arrs in SECTEURS_2026.items():
            if arr in arrs:
                secteur = s
                break

        if secteur and secteur in seats_by_sector:
            winner = seats_by_sector[secteur].get("winner", "")
            famille = familles.get(winner, "DIV") if familles else "DIV"
            color = get_color(famille)
            score = seats_by_sector[secteur].get("score", 0)

            folium.CircleMarker(
                location=coords,
                radius=18,
                color="white",
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"<b>{arr}</b><br>{winner}<br>{score:.1f}%"
            ).add_to(m)

            # Label
            folium.Marker(
                location=coords,
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 10px; color: white; font-weight: bold; text-align: center;">{arr.replace("e", "").replace("er", "")}</div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15)
                )
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=coords,
                radius=15,
                color="white",
                fill=True,
                fill_color="#95A5A6",
                fill_opacity=0.6,
                popup=arr
            ).add_to(m)

    return m


# =============================================================================
# HEADER - Fira.money style (full width)
# =============================================================================

# Container pour le header
header_container = st.container()
with header_container:
    st.markdown("""
    <div style="background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 12px; padding: 16px 20px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div>
                <h1 style="font-size: 24px; font-weight: 700; color: white; margin: 0;">
                    Municipales Paris <span style="color: #f97316;">2026</span>
                </h1>
                <p style="color: #6b7280; font-size: 13px; margin: 4px 0 0 0;">
                    Simulateur électoral | Conseil de Paris | 163 sièges
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Row avec métriques et boutons
    hcol1, hcol2, hcol3, hcol4, hcol5 = st.columns([1.5, 1, 1, 1.2, 1.2])

    with hcol1:
        mode_expert = st.toggle("Mode expert", value=False, key="mode_expert")

    with hcol2:
        st.markdown("""
        <div style="text-align: center;">
            <p style="color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0;">Prime</p>
            <p style="color: #f97316; font-size: 22px; font-weight: 700; margin: 0;">25%</p>
        </div>
        """, unsafe_allow_html=True)

    with hcol3:
        st.markdown("""
        <div style="text-align: center;">
            <p style="color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0;">Majorité</p>
            <p style="color: #22c55e; font-size: 22px; font-weight: 700; margin: 0;">82</p>
        </div>
        """, unsafe_allow_html=True)

    with hcol4:
        simulate_btn = st.button("▶ Simuler", type="primary", use_container_width=True, key="header_simulate")
        if simulate_btn:
            st.session_state["trigger_simulation"] = True

    with hcol5:
        # Export PDF button (visible only when results exist)
        if "r1" in st.session_state or "final_seats" in st.session_state:
            if st.button("📄 Export", key="export_pdf_btn", use_container_width=True):
                st.session_state["show_pdf_export"] = True
        else:
            st.markdown('<div style="height: 38px"></div>', unsafe_allow_html=True)

# =============================================================================
# DONNÉES DES SONDAGES
# =============================================================================

SONDAGES = {
    "Cluster17/Politico — 2 février 2026": {
        "date": "2026-02-02",
        "institut": "Cluster17",
        "commanditaire": "Politico",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "PS-Écolos-PCF", "famille": "PS", "score": 33.0},
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 26.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 14.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 10.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 4.0},
        ],
    },
    "IFOP-Fiducial/Sud Radio — 24 janvier 2026": {
        "date": "2026-01-24",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Sud Radio",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "PS-Écolos-PCF", "famille": "PS", "score": 32.0},
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 28.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 14.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 9.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 5.0},
        ],
    },
    "ELABE — 10 janvier 2026": {
        "date": "2026-01-10",
        "institut": "ELABE",
        "commanditaire": "BFMTV",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "PS-Écolos-PCF", "famille": "PS", "score": 33.0},
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 26.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 16.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 9.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 5.0},
        ],
    },
    "IFOP-Fiducial/Sud Radio — 10 janvier 2026": {
        "date": "2026-01-10",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Sud Radio",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "PS-Écolos-PCF", "famille": "PS", "score": 30.0},
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 28.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 16.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 8.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 7.0},
        ],
    },
    "Cluster17/Politico — 28 novembre 2025": {
        "date": "2025-11-28",
        "institut": "Cluster17",
        "commanditaire": "Politico",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "PS-Écolos-PCF", "famille": "PS", "score": 30.0},
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 27.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 15.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 12.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 6.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 6.0},
        ],
    },
    "IFOP-Fiducial — 5 novembre 2025": {
        "date": "2025-11-05",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Le Figaro",
        "listes": [
            {"nom": "Rachida Dati", "parti": "LR-MoDem-UDI", "famille": "LR", "score": 26.0},
            {"nom": "Emmanuel Grégoire", "parti": "PS-PCF", "famille": "PS", "score": 20.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons-Renaissance", "famille": "REN", "score": 14.0},
            {"nom": "David Belliard", "parti": "EELV", "famille": "EELV", "score": 13.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 12.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 8.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 7.0},
        ],
    },
    "Personnalisé": {
        "date": "",
        "institut": "",
        "commanditaire": "",
        "listes": [
            {"nom": "Emmanuel Grégoire", "parti": "Gauche unie", "famille": "PS", "score": 32.0},
            {"nom": "Rachida Dati", "parti": "LR", "famille": "LR", "score": 28.0},
            {"nom": "Pierre-Yves Bournazel", "parti": "Horizons", "famille": "REN", "score": 14.0},
            {"nom": "Sophia Chikirou", "parti": "LFI", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo", "parti": "Reconquête", "famille": "REC", "score": 9.0},
            {"nom": "Thierry Mariani", "parti": "RN", "famille": "RN", "score": 5.0},
        ],
    },
}

# =============================================================================
# SCÉNARIOS DE SECOND TOUR (IFOP-Fiducial, janvier 2026)
# =============================================================================

SCENARIOS_T2 = {
    "Duel Grégoire-Dati": {
        "description": "Face à face gauche-droite",
        "source": "IFOP-Fiducial, 24 janvier 2026",
        "listes": [
            {"nom": "Emmanuel Grégoire", "famille": "PS", "score": 50.0},
            {"nom": "Rachida Dati", "famille": "LR", "score": 50.0},
        ],
    },
    "Triangulaire + LFI": {
        "description": "Chikirou se maintient → avantage Dati",
        "source": "IFOP-Fiducial, 24 janvier 2026",
        "listes": [
            {"nom": "Rachida Dati", "famille": "LR", "score": 45.0},
            {"nom": "Emmanuel Grégoire", "famille": "PS", "score": 41.0},
            {"nom": "Sophia Chikirou", "famille": "LFI", "score": 14.0},
        ],
    },
    "Triangulaire + Horizons": {
        "description": "Bournazel se maintient → avantage Grégoire",
        "source": "IFOP-Fiducial, 24 janvier 2026",
        "listes": [
            {"nom": "Emmanuel Grégoire", "famille": "PS", "score": 43.0},
            {"nom": "Rachida Dati", "famille": "LR", "score": 41.0},
            {"nom": "Pierre-Yves Bournazel", "famille": "REN", "score": 16.0},
        ],
    },
    "Quadrangulaire": {
        "description": "LFI + Reconquête se maintiennent → match nul",
        "source": "IFOP-Fiducial, 24 janvier 2026",
        "listes": [
            {"nom": "Emmanuel Grégoire", "famille": "PS", "score": 38.0},
            {"nom": "Rachida Dati", "famille": "LR", "score": 38.0},
            {"nom": "Sophia Chikirou", "famille": "LFI", "score": 12.0},
            {"nom": "Sarah Knafo", "famille": "REC", "score": 12.0},
        ],
    },
    "Personnalisé": {
        "description": "Configurer manuellement",
        "source": "",
        "listes": [],
    },
}

# =============================================================================
# INITIALISATION
# =============================================================================

import copy

if "sondage_selectionne" not in st.session_state:
    st.session_state["sondage_selectionne"] = list(SONDAGES.keys())[0]

if "listes" not in st.session_state:
    st.session_state["listes"] = copy.deepcopy(SONDAGES[st.session_state["sondage_selectionne"]]["listes"])

# =============================================================================
# NAVIGATION TABS
# =============================================================================

tab1, tab2, tab3 = st.tabs(["Premier Tour", "Second Tour", "Résultats"])

# =============================================================================
# TAB 1: PREMIER TOUR
# =============================================================================

with tab1:
    st.markdown('<div style="height: 20px"></div>', unsafe_allow_html=True)

    # Sélecteur de sondage
    st.markdown('<p class="section-header">Sélectionner un sondage</p>', unsafe_allow_html=True)

    col_select, col_info = st.columns([2, 1])

    with col_select:
        sondage_options = list(SONDAGES.keys())
        selected_sondage = st.selectbox(
            "Sondage",
            options=sondage_options,
            index=sondage_options.index(st.session_state.get("sondage_selectionne", sondage_options[0])),
            label_visibility="collapsed",
        )

        # Charger le sondage si changement
        if selected_sondage != st.session_state.get("sondage_selectionne"):
            st.session_state["sondage_selectionne"] = selected_sondage
            st.session_state["listes"] = copy.deepcopy(SONDAGES[selected_sondage]["listes"])
            # Reset simulation
            if "r1" in st.session_state:
                del st.session_state["r1"]
            st.rerun()

    with col_info:
        sondage_data = SONDAGES[selected_sondage]
        if sondage_data["institut"]:
            st.markdown(f"""
            <div style="padding: 8px 16px; background: rgba(99, 102, 241, 0.1); border-radius: 8px;
                        border: 1px solid rgba(99, 102, 241, 0.3); color: rgba(255,255,255,0.8); font-size: 13px;">
                <strong>{sondage_data["institut"]}</strong> pour {sondage_data["commanditaire"]}
            </div>
            """, unsafe_allow_html=True)

    # Graphique d'évolution des sondages (mode expert uniquement)
    if mode_expert:
        st.markdown('<p class="section-header">Évolution des sondages</p>', unsafe_allow_html=True)

        # Préparer les données
        evolution_data = []
        for sondage_name, sondage_info in SONDAGES.items():
            if sondage_info["date"]:
                for liste in sondage_info["listes"]:
                    evolution_data.append({
                        "Date": sondage_info["date"],
                        "Candidat": liste["nom"],
                        "Score": liste["score"],
                        "Famille": liste["famille"],
                    })

        if evolution_data:
            evo_df = pd.DataFrame(evolution_data)
            evo_df["Date"] = pd.to_datetime(evo_df["Date"])
            evo_df = evo_df.sort_values("Date")

            # Dates uniques
            dates = sorted(evo_df["Date"].unique())
            date_labels = [pd.to_datetime(d).strftime("%d %b") for d in dates]

            # Trier candidats par dernier score
            last_scores = evo_df.sort_values("Date").groupby("Candidat").last()["Score"].sort_values(ascending=False)
            sorted_candidates = last_scores.index.tolist()

            # Couleurs par candidat
            candidate_styles = {
                "Emmanuel Grégoire": {"color": "#FF6B6B", "symbol": "circle"},
                "Rachida Dati": {"color": "#339AF0", "symbol": "diamond"},
                "Pierre-Yves Bournazel": {"color": "#FCC419", "symbol": "triangle"},
                "Sophia Chikirou": {"color": "#F06595", "symbol": "rect"},
                "Sarah Knafo": {"color": "#20C997", "symbol": "roundRect"},
                "Thierry Mariani": {"color": "#845EF7", "symbol": "pin"},
                "David Belliard": {"color": "#51CF66", "symbol": "circle"},
            }

            series = []
            active_candidates = []  # Candidats présents dans les sondages récents

            # Dernière date de sondage
            last_date = max(dates)

            for idx, candidat in enumerate(sorted_candidates):
                df_cand = evo_df[evo_df["Candidat"] == candidat]
                style = candidate_styles.get(candidat, {"color": "#868E96", "symbol": "circle"})
                color = style["color"]
                symbol = style["symbol"]

                score_by_date = dict(zip(df_cand["Date"], df_cand["Score"]))

                # Vérifier si le candidat est présent dans le dernier sondage
                if last_date not in score_by_date:
                    continue  # Ignorer les candidats qui ne sont plus présents

                data = []
                for d in dates:
                    score = score_by_date.get(d)
                    data.append(score if score is not None else "-")

                # Dernier score pour déterminer le style
                scores_list = [s for s in data if s != "-"]
                last_score = scores_list[-1] if scores_list else 0

                # Style selon position par rapport au seuil
                is_below = last_score < 10
                line_width = 2 if is_below else 2.5
                opacity = 0.5 if is_below else 1.0

                active_candidates.append(candidat)
                series.append({
                    "name": candidat.split()[-1],
                    "type": "line",
                    "data": data,
                    "smooth": 0.3,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "showSymbol": True,
                    "lineStyle": {
                        "width": line_width,
                        "color": color,
                        "opacity": opacity,
                    },
                    "itemStyle": {
                        "color": color,
                        "borderColor": "#0a0a0a",
                        "borderWidth": 2,
                    },
                    "emphasis": {
                        "focus": "series",
                        "lineStyle": {"width": 3},
                        "itemStyle": {"borderWidth": 0},
                    },
                    "connectNulls": True,
                    "z": 10,
                })

            # Zone seuil 10% - zone colorée sans ligne
            series.append({
                "name": "Seuil 10%",
                "type": "line",
                "data": [10] * len(dates),
                "lineStyle": {"width": 0},  # Pas de ligne
                "symbol": "none",
                "itemStyle": {"color": "#ef4444"},
                "z": 0,
                "areaStyle": {
                    "color": "rgba(239, 68, 68, 0.15)",
                    "origin": "start"
                },
                "silent": True,
            })

            legend_names = [c.split()[-1] for c in active_candidates]

            option = {
                "tooltip": {
                    "trigger": "axis",
                    "backgroundColor": "rgba(20, 20, 20, 0.95)",
                    "borderColor": "rgba(255,255,255,0.08)",
                    "borderWidth": 1,
                    "textStyle": {"color": "#fff", "fontSize": 12},
                    "padding": [12, 16],
                },
                "legend": {
                    "data": legend_names,
                    "top": 8,
                    "left": "center",
                    "textStyle": {"color": "#9ca3af", "fontSize": 12},
                    "itemGap": 24,
                    "itemWidth": 20,
                    "itemHeight": 10,
                    "icon": "roundRect",
                },
                "grid": {
                    "left": 55,
                    "right": 25,
                    "top": 60,
                    "bottom": 45,
                    "containLabel": False
                },
                "xAxis": {
                    "type": "category",
                    "data": date_labels,
                    "axisLabel": {
                        "color": "#6b7280",
                        "fontSize": 11,
                        "margin": 14
                    },
                    "axisLine": {"show": False},
                    "axisTick": {"show": False},
                    "boundaryGap": False,
                },
                "yAxis": {
                    "type": "value",
                    "min": 0,
                    "max": 40,
                    "interval": 10,
                    "axisLabel": {
                        "color": "#6b7280",
                        "fontSize": 11,
                        "formatter": "{value}%"
                    },
                    "splitLine": {
                        "lineStyle": {
                            "color": "rgba(255,255,255,0.06)",
                            "type": "solid"
                        }
                    },
                    "axisLine": {"show": False},
                    "axisTick": {"show": False},
                },
                "series": series,
            }

            st_echarts(options=option, height="420px")

            st.markdown("""
            <p style="color: #6b7280; font-size: 11px; text-align: center; margin-top: 4px;">
                <span style="color: rgba(239, 68, 68, 0.6);">▮</span> Zone d'élimination (&lt;10%) ·
                Sources : IFOP, ELABE, Cluster17
            </p>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height: 20px"></div>', unsafe_allow_html=True)

    st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.markdown('<p class="section-header">Candidats</p>', unsafe_allow_html=True)

        familles_options = list(COLORS.keys())
        n_listes = len(st.session_state["listes"])

        for i in range(n_listes):
            liste = st.session_state["listes"][i]
            cols = st.columns([3, 2, 2, 1.5, 0.5])

            # Initialiser les clés dans session_state si nécessaire
            if f"nom_{i}" not in st.session_state:
                st.session_state[f"nom_{i}"] = liste["nom"]
            if f"parti_{i}" not in st.session_state:
                st.session_state[f"parti_{i}"] = liste.get("parti", "")
            if f"famille_{i}" not in st.session_state:
                st.session_state[f"famille_{i}"] = liste["famille"]
            if f"score_{i}" not in st.session_state:
                st.session_state[f"score_{i}"] = float(liste["score"])

            with cols[0]:
                st.text_input(
                    "Candidat",
                    key=f"nom_{i}",
                    label_visibility="collapsed",
                    placeholder="Nom du candidat"
                )

            with cols[1]:
                st.text_input(
                    "Parti",
                    key=f"parti_{i}",
                    label_visibility="collapsed",
                    placeholder="Parti"
                )

            with cols[2]:
                default_idx = familles_options.index(liste["famille"]) if liste["famille"] in familles_options else 0
                st.selectbox(
                    "Famille",
                    options=familles_options,
                    index=default_idx,
                    key=f"famille_{i}",
                    label_visibility="collapsed"
                )

            with cols[3]:
                st.number_input(
                    "Score",
                    min_value=0.0,
                    max_value=60.0,
                    step=0.5,
                    key=f"score_{i}",
                    label_visibility="collapsed"
                )

            with cols[4]:
                if st.button("✕", key=f"del_{i}", help="Supprimer"):
                    # Supprimer les clés associées
                    for key in [f"nom_{i}", f"parti_{i}", f"famille_{i}", f"score_{i}"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state["listes"].pop(i)
                    st.rerun()

        # Add button
        if st.button("+ Ajouter un candidat", use_container_width=True):
            new_idx = len(st.session_state["listes"])
            st.session_state["listes"].append({
                "nom": "", "parti": "", "famille": "DIV", "score": 5.0
            })
            st.rerun()

    with col_side:
        st.markdown('<p class="section-header">Paramètres</p>', unsafe_allow_html=True)

        # Calculer le total depuis les widgets
        total = sum(
            st.session_state.get(f"score_{i}", 0.0)
            for i in range(len(st.session_state["listes"]))
        )

        # Total indicator
        if abs(total - 100) < 1:
            st.success(f"Total : {total:.0f}%")
        else:
            st.warning(f"Total : {total:.1f}%")

        st.markdown('<div style="height: 16px"></div>', unsafe_allow_html=True)

        participation_t1 = st.slider(
            "Participation",
            min_value=25, max_value=65, value=45,
            format="%d%%"
        ) / 100

        st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

        # Visualisation mini
        st.markdown('<p class="section-header">Aperçu</p>', unsafe_allow_html=True)

        for l in sorted(st.session_state["listes"], key=lambda x: -x["score"]):
            pct = l["score"] / total * 100 if total > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.9);">{l['nom'][:20]}</span>
                    <span style="font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9);">{l['score']:.0f}%</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {pct}%; background: {get_color(l['famille'])};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Simulation triggered from header button
    if st.session_state.get("trigger_simulation"):
        inscrits = 1_400_000
        exprimes = int(inscrits * participation_t1)

        # Lire les valeurs actuelles des widgets
        n_listes = len(st.session_state["listes"])
        current_listes = []
        for i in range(n_listes):
            current_listes.append({
                "nom": st.session_state.get(f"nom_{i}", ""),
                "parti": st.session_state.get(f"parti_{i}", ""),
                "famille": st.session_state.get(f"famille_{i}", "DIV"),
                "score": st.session_state.get(f"score_{i}", 0.0),
            })

        total = sum(l["score"] for l in current_listes)

        votes_t1 = {}
        familles_t1 = {}
        for l in current_listes:
            if l["nom"]:  # Ignorer les listes sans nom
                votes_t1[l["nom"]] = int(l["score"] / total * exprimes) if total > 0 else 0
                familles_t1[l["nom"]] = l["famille"]

        r1 = run_round1(votes_t1, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)

        st.session_state["r1"] = r1
        st.session_state["votes_t1"] = votes_t1
        st.session_state["familles_t1"] = familles_t1
        st.session_state["participation_t1"] = participation_t1
        st.session_state["inscrits"] = inscrits
        st.session_state["trigger_simulation"] = False  # Reset trigger

        st.success("✓ Simulation effectuée")

    # Results T1
    if "r1" in st.session_state:
        r1 = st.session_state["r1"]
        familles_t1 = st.session_state.get("familles_t1", {})

        st.markdown('<div style="height: 32px"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-header">Résultats du 1er tour</p>', unsafe_allow_html=True)

        if r1.resolved:
            st.balloons()
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                        padding: 32px; border-radius: 16px; text-align: center; color: white;">
                <p style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Victoire au 1er tour</p>
                <h2 style="font-size: 28px; font-weight: 700; margin: 0;">{r1.winner}</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Qualifiés** <span style='color: #4ade80'>≥10%</span>", unsafe_allow_html=True)
                for liste in r1.qualified:
                    pct = r1.percentages[liste] * 100
                    color = get_color(familles_t1.get(liste, "DIV"))
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; padding: 8px 0; color: rgba(255,255,255,0.9);">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                        <span style="flex: 1;">{liste}</span>
                        <span style="font-weight: 600;">{pct:.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("**Fusion possible** <span style='color: #fbbf24'>5-10%</span>", unsafe_allow_html=True)
                if r1.fusionable:
                    for liste in r1.fusionable:
                        pct = r1.percentages[liste] * 100
                        color = get_color(familles_t1.get(liste, "DIV"))
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; padding: 8px 0; color: rgba(255,255,255,0.9);">
                            <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                            <span style="flex: 1;">{liste}</span>
                            <span style="font-weight: 600;">{pct:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("Aucun")

            with col3:
                st.markdown("**Éliminés** <span style='color: #f87171'><5%</span>", unsafe_allow_html=True)
                if r1.eliminated:
                    for liste in r1.eliminated:
                        pct = r1.percentages[liste] * 100
                        color = get_color(familles_t1.get(liste, "DIV"))
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; padding: 8px 0; opacity: 0.5; color: rgba(255,255,255,0.9);">
                            <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                            <span style="flex: 1;">{liste}</span>
                            <span style="font-weight: 600;">{pct:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("Aucun")

# =============================================================================
# TAB 2: SECOND TOUR
# =============================================================================

with tab2:
    st.markdown('<div style="height: 20px"></div>', unsafe_allow_html=True)

    # Sélecteur de scénario T2 (toujours visible)
    st.markdown('<p class="section-header">Scénarios de second tour (IFOP-Fiducial)</p>', unsafe_allow_html=True)

    scenario_col1, scenario_col2 = st.columns([2, 3])

    with scenario_col1:
        scenario_options = list(SCENARIOS_T2.keys())
        selected_scenario = st.selectbox(
            "Hypothèse",
            options=scenario_options,
            index=0,
            key="scenario_t2_select",
            label_visibility="collapsed"
        )

    with scenario_col2:
        scenario_data = SCENARIOS_T2[selected_scenario]
        if scenario_data["source"]:
            st.markdown(f"""
            <div style="padding: 8px 16px; background: rgba(249, 115, 22, 0.1); border-radius: 8px;
                        border: 1px solid rgba(249, 115, 22, 0.3); color: rgba(255,255,255,0.8); font-size: 13px;">
                <strong style="color: #f97316;">{scenario_data['description']}</strong>
                <span style="color: #6b7280; margin-left: 8px;">— {scenario_data['source']}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="padding: 8px 16px; background: rgba(255,255,255,0.05); border-radius: 8px;
                        border: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); font-size: 13px;">
                {scenario_data['description']}
            </div>
            """, unsafe_allow_html=True)

    # Afficher les scores du scénario sélectionné
    if selected_scenario != "Personnalisé" and scenario_data["listes"]:
        st.markdown('<div style="height: 16px"></div>', unsafe_allow_html=True)

        # Afficher les listes du scénario
        scenario_cols = st.columns(len(scenario_data["listes"]))
        for idx, liste in enumerate(scenario_data["listes"]):
            with scenario_cols[idx]:
                color = get_color(liste["famille"])
                is_winner = liste["score"] == max(l["score"] for l in scenario_data["listes"])
                border_color = "#22c55e" if is_winner else "#2a2a2a"
                st.markdown(f"""
                <div style="background: #141414; border: 2px solid {border_color}; border-radius: 8px;
                            padding: 12px; text-align: center;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: {color};
                                margin: 0 auto 8px auto;"></div>
                    <p style="color: white; font-weight: 600; margin: 0; font-size: 14px;">
                        {liste['nom'].split()[-1]}
                    </p>
                    <p style="color: #f97316; font-size: 24px; font-weight: 700; margin: 4px 0 0 0;">
                        {liste['score']:.0f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div style="height: 8px"></div>', unsafe_allow_html=True)

        # Bouton pour simuler ce scénario
        if st.button("▶ Simuler ce scénario", type="primary", key="simulate_scenario_t2"):
            # Créer les votes pour ce scénario
            inscrits = st.session_state.get("inscrits", 1_400_000)
            participation = st.session_state.get("participation_t1", 0.5)
            exprimes = int(inscrits * participation)

            votes_t2 = {}
            familles_t2 = {}
            for liste in scenario_data["listes"]:
                votes_t2[liste["nom"]] = int(liste["score"] / 100 * exprimes)
                familles_t2[liste["nom"]] = liste["famille"]

            st.session_state["votes_t2"] = votes_t2
            st.session_state["listes_t2"] = scenario_data["listes"]
            st.session_state["familles_t1"] = familles_t2  # Update families

            # Run simulation
            r2 = run_round2(votes_t2, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)
            st.session_state["r2"] = r2
            st.session_state["final_seats"] = r2.seats

            st.success("✓ Scénario simulé — voir l'onglet Résultats")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Section configuration manuelle (si T1 simulé)
    if "r1" not in st.session_state:
        st.info("💡 Simulez d'abord le premier tour pour configurer manuellement les retraits et fusions")
    elif st.session_state["r1"].resolved:
        st.info("L'élection a été décidée au premier tour")
    else:
        st.markdown('<p class="section-header">Configuration manuelle</p>', unsafe_allow_html=True)

        r1 = st.session_state["r1"]
        votes_t1 = st.session_state["votes_t1"]
        familles_t1 = st.session_state.get("familles_t1", {})

        col_main, col_side = st.columns([2, 1])

        with col_main:
            # Fusions
            if r1.fusionable:
                st.markdown('<p class="section-header">Fusions</p>', unsafe_allow_html=True)

                fusions = {}
                for liste in r1.fusionable:
                    pct = r1.percentages[liste] * 100
                    famille_src = familles_t1.get(liste, "DIV")
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        color = get_color(famille_src)
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; height: 38px; color: rgba(255,255,255,0.9);">
                            <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                            <span>{liste} ({pct:.0f}%)</span>
                            <span style="margin-left: 6px; color: rgba(255,255,255,0.4); font-size: 11px;">[{famille_src}]</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        target = st.selectbox(
                            "→", options=["Ne fusionne pas"] + r1.qualified,
                            key=f"fus_{liste}", label_visibility="collapsed"
                        )
                    with col3:
                        if target != "Ne fusionne pas":
                            famille_tgt = familles_t1.get(target, "DIV")
                            auto_rate = get_transfer_rate(famille_src, famille_tgt)
                            st.markdown(f"""
                            <div style="text-align: center; padding: 6px; background: rgba(99, 102, 241, 0.15);
                                        border-radius: 6px; color: rgba(255,255,255,0.8); font-size: 13px;">
                                {auto_rate*100:.0f}%
                            </div>
                            """, unsafe_allow_html=True)
                            fusions[liste] = {"target": target, "rate": auto_rate, "famille_src": famille_src}

                st.session_state["fusions"] = fusions
                st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

            # Maintiens / Retraits
            st.markdown('<p class="section-header">Maintien ou retrait</p>', unsafe_allow_html=True)

            maintiens = {}
            desistements = {}

            for liste in r1.qualified:
                pct = r1.percentages[liste] * 100
                famille_src = familles_t1.get(liste, "DIV")
                color = get_color(famille_src)

                col1, col2, col3, col4 = st.columns([2.5, 1, 2, 1])

                with col1:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; height: 38px; color: rgba(255,255,255,0.9);">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                        <span style="font-weight: 500;">{liste}</span>
                        <span style="margin-left: 6px; color: rgba(255,255,255,0.4); font-size: 11px;">[{famille_src}]</span>
                        <span style="margin-left: 8px; color: rgba(255,255,255,0.5);">({pct:.0f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    action = st.radio(
                        "act", ["Maintien", "Retrait"],
                        key=f"act_{liste}", horizontal=True, label_visibility="collapsed"
                    )

                with col3:
                    if action == "Retrait":
                        autres = [l for l in r1.qualified if l != liste]
                        if autres:
                            benef = st.selectbox(
                                "Report →", options=autres,
                                key=f"ben_{liste}", label_visibility="collapsed"
                            )
                            famille_tgt = familles_t1.get(benef, "DIV")
                            auto_rate = get_transfer_rate(famille_src, famille_tgt)
                            desistements[liste] = {
                                "beneficiary": benef,
                                "rate": auto_rate,
                                "famille_src": famille_src,
                                "famille_tgt": famille_tgt
                            }
                    else:
                        maintiens[liste] = True

                with col4:
                    if action == "Retrait" and liste in desistements:
                        rate = desistements[liste]["rate"]
                        st.markdown(f"""
                        <div style="text-align: center; padding: 6px; background: rgba(251, 191, 36, 0.15);
                                    border-radius: 6px; color: rgba(255,255,255,0.8); font-size: 13px;">
                            {rate*100:.0f}%
                        </div>
                        """, unsafe_allow_html=True)

            st.session_state["maintiens"] = maintiens
            st.session_state["desistements"] = desistements

            # Afficher la matrice de transfert utilisée
            if desistements:
                with st.expander("📊 Détail des reports", expanded=False):
                    st.markdown("""
                    <p style="font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 12px;">
                        Taux calculés selon la matrice de transfert (études IPSOS/IFOP 2024)
                    </p>
                    """, unsafe_allow_html=True)
                    for src, data in desistements.items():
                        src_fam = data.get("famille_src", "?")
                        tgt_fam = data.get("famille_tgt", "?")
                        rate = data["rate"]
                        benef = data["beneficiary"]
                        st.markdown(f"""
                        <div style="padding: 8px 12px; background: rgba(255,255,255,0.03);
                                    border-radius: 6px; margin-bottom: 6px; font-size: 13px;">
                            <span style="color: rgba(255,255,255,0.7);">{src}</span>
                            <span style="color: rgba(255,255,255,0.4);"> [{src_fam}] → [{tgt_fam}] </span>
                            <span style="color: rgba(255,255,255,0.7);">{benef}</span>
                            <span style="float: right; color: #fbbf24; font-weight: 600;">{rate*100:.0f}%</span>
                        </div>
                        """, unsafe_allow_html=True)

        with col_side:
            st.markdown('<p class="section-header">Participation T2</p>', unsafe_allow_html=True)

            part_t1 = st.session_state["participation_t1"] * 100
            delta = st.slider(
                "Variation", min_value=-10, max_value=+15, value=+3,
                format="%+d pts"
            )
            participation_t2 = (part_t1 + delta) / 100
            st.session_state["participation_t2"] = participation_t2

            st.metric("Participation T2", f"{participation_t2*100:.0f}%")

            st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-header">Configuration</p>', unsafe_allow_html=True)

            listes_t2 = [l for l in r1.qualified if l in maintiens]
            n = len(listes_t2)

            if n == 2:
                st.info("Duel")
            elif n == 3:
                st.warning("Triangulaire")
            elif n >= 4:
                st.error("Quadrangulaire")

            # Calculer votes T2
            votes_t2 = {}
            fusions = st.session_state.get("fusions", {})

            for liste in listes_t2:
                base = votes_t1[liste]
                for src, data in fusions.items():
                    if data["target"] == liste:
                        base += int(votes_t1.get(src, 0) * data["rate"])
                for src, data in desistements.items():
                    if data["beneficiary"] == liste:
                        base += int(votes_t1.get(src, 0) * data["rate"])
                votes_t2[liste] = base

            # Ajuster participation
            inscrits = st.session_state["inscrits"]
            total_v = sum(votes_t2.values())
            target_v = int(inscrits * participation_t2)
            if total_v > 0:
                ratio = target_v / total_v
                votes_t2 = {k: int(v * ratio) for k, v in votes_t2.items()}

            st.session_state["votes_t2"] = votes_t2
            st.session_state["listes_t2"] = listes_t2

# =============================================================================
# TAB 3: RÉSULTATS
# =============================================================================

with tab3:
    st.markdown('<div style="height: 20px"></div>', unsafe_allow_html=True)

    seats = None

    if "r1" not in st.session_state:
        st.info("Simulez d'abord le premier tour")
    elif st.session_state["r1"].resolved:
        seats = st.session_state["r1"].seats
    elif "votes_t2" not in st.session_state or not st.session_state.get("listes_t2"):
        st.info("Configurez d'abord le second tour")
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Simuler le 2nd tour →", type="primary", use_container_width=True):
                votes_t2 = st.session_state["votes_t2"]
                r2 = run_round2(votes_t2, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)
                st.session_state["r2"] = r2
                st.session_state["final_seats"] = r2.seats

        seats = st.session_state.get("final_seats")

    if seats:
        familles_t1 = st.session_state.get("familles_t1", {})

        winner = max(seats, key=seats.get)
        winner_seats = seats[winner]
        winner_color = get_color(familles_t1.get(winner, "DIV"))
        has_majority = winner_seats >= MAYOR_ABSOLUTE_MAJORITY

        # Hero section
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {winner_color}dd 0%, {winner_color}99 100%);
                    padding: 48px; border-radius: 20px; text-align: center; color: white; margin-bottom: 32px;">
            <p style="font-size: 14px; opacity: 0.9; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 2px;">
                {"Majorité absolue" if has_majority else "Vainqueur sans majorité"}
            </p>
            <h1 style="font-size: 36px; font-weight: 700; margin: 0 0 8px 0;">{winner}</h1>
            <p style="font-size: 48px; font-weight: 700; margin: 0;">{winner_seats} <span style="font-size: 24px; opacity: 0.8;">/ {CONSEIL_PARIS_SEATS}</span></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown('<p class="section-header">Répartition des sièges</p>', unsafe_allow_html=True)

            # Horizontal bar chart
            fig = go.Figure()

            for liste in sorted(seats.keys(), key=lambda x: -seats[x]):
                if seats[liste] > 0:
                    color = get_color(familles_t1.get(liste, "DIV"))
                    fig.add_trace(go.Bar(
                        y=[liste],
                        x=[seats[liste]],
                        orientation='h',
                        marker_color=color,
                        text=f"{seats[liste]}",
                        textposition='inside',
                        textfont=dict(color='white', size=14, family='Inter'),
                        hovertemplate=f"{liste}: %{{x}} sièges<extra></extra>"
                    ))

            fig.add_vline(x=MAYOR_ABSOLUTE_MAJORITY, line_dash="dot", line_color="#E74C3C", line_width=2)
            fig.add_annotation(x=MAYOR_ABSOLUTE_MAJORITY, y=1.1, yref="paper",
                              text=f"Majorité ({MAYOR_ABSOLUTE_MAJORITY})", showarrow=False,
                              font=dict(size=11, color="#E74C3C"))

            fig.update_layout(
                showlegend=False,
                height=300,
                margin=dict(l=0, r=40, t=20, b=20),
                xaxis=dict(range=[0, CONSEIL_PARIS_SEATS + 10], showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=False, tickfont=dict(color='rgba(255,255,255,0.8)')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', color='rgba(255,255,255,0.8)'),
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<p class="section-header">Analyse</p>', unsafe_allow_html=True)

            # Par bloc
            blocs_seats = {"Gauche": 0, "Centre": 0, "Droite": 0, "Ext. Droite": 0}
            for liste, n in seats.items():
                bloc = get_bloc(familles_t1.get(liste, "DIV"))
                if bloc in blocs_seats:
                    blocs_seats[bloc] += n

            for bloc, n in blocs_seats.items():
                if n > 0:
                    pct = n / CONSEIL_PARIS_SEATS * 100
                    st.markdown(f"""
                    <div class="analysis-row">
                        <span>{bloc}</span>
                        <span class="analysis-value">{n} <span class="analysis-pct">({pct:.0f}%)</span></span>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

            # Coalitions
            st.markdown('<p class="section-header">Coalitions</p>', unsafe_allow_html=True)

            coalitions = [
                ("Gauche", blocs_seats["Gauche"]),
                ("Gauche + Centre", blocs_seats["Gauche"] + blocs_seats["Centre"]),
                ("Droite + Centre", blocs_seats["Droite"] + blocs_seats["Centre"]),
            ]

            for name, total in coalitions:
                if total >= MAYOR_ABSOLUTE_MAJORITY:
                    st.markdown(f"""
                    <div class="coalition-success">
                        {name} : <strong>{total}</strong>
                    </div>
                    """, unsafe_allow_html=True)

        # =====================================================================
        # CARTE DE PARIS (mode expert)
        # =====================================================================
        if mode_expert:
            st.markdown('<div style="height: 32px"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-header">🗺️ Carte de Paris</p>', unsafe_allow_html=True)

            with st.expander("Visualisation géographique", expanded=False):
                st.markdown("""
                <p style="color: rgba(255,255,255,0.6); font-size: 13px; margin-bottom: 16px;">
                    Carte indicative des résultats par arrondissement (simulation uniforme).
                    Les scores sont extrapolés à partir des résultats globaux.
                </p>
                """, unsafe_allow_html=True)

                # Créer les données par arrondissement (simulation simplifiée)
                # En l'absence de données sectorielles, on utilise les scores globaux
                r1_result = st.session_state.get("r1")
                if r1_result and hasattr(r1_result, "percentages"):
                    winner = max(r1_result.percentages, key=r1_result.percentages.get)
                    winner_score = r1_result.percentages[winner]

                    # Simuler des résultats par arrondissement (variations aléatoires)
                    seats_by_sector = {}
                    for secteur in SECTEURS_2026:
                        seats_by_sector[secteur] = {
                            "winner": winner,
                            "score": winner_score
                        }

                    paris_map = create_paris_map(seats_by_sector, familles_t1)
                else:
                    paris_map = create_paris_map()

                st_folium(paris_map, width=700, height=500, returned_objects=[])

                st.markdown("""
                <p style="color: rgba(255,255,255,0.5); font-size: 11px; text-align: center; margin-top: 8px;">
                    Carte indicative · Données uniformes · Cliquez sur un arrondissement pour les détails
                </p>
                """, unsafe_allow_html=True)

        # =====================================================================
        # EXPORT PDF
        # =====================================================================
        st.markdown('<div style="height: 32px"></div>', unsafe_allow_html=True)

        if st.session_state.get("show_pdf_export"):
            st.markdown('<p class="section-header">📄 Export du rapport</p>', unsafe_allow_html=True)
            mc_results = st.session_state.get("mc_results")
            html_bytes = generate_pdf_report(seats, familles_t1, mc_results=mc_results)
            filename = f"simulation_paris_2026_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
            st.markdown(get_download_link(html_bytes, filename), unsafe_allow_html=True)
            st.markdown('<p style="color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 8px;">Le fichier HTML peut être ouvert dans un navigateur et imprimé en PDF.</p>', unsafe_allow_html=True)
            if st.button("Fermer", key="close_pdf"):
                st.session_state["show_pdf_export"] = False
                st.rerun()

        # =====================================================================
        # MONTE CARLO SIMULATION (mode expert)
        # =====================================================================
        if mode_expert:
            st.markdown('<div style="height: 32px"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-header">🎲 Simulation Monte Carlo</p>', unsafe_allow_html=True)

            with st.expander("Quantifier l'incertitude sur les résultats", expanded=False):
                st.markdown("""
                <p style="color: rgba(255,255,255,0.6); font-size: 13px; margin-bottom: 16px;">
                    La simulation Monte Carlo perturbe les scores N fois pour estimer la distribution probable des sièges
                    et quantifier l'incertitude liée aux erreurs de sondage.
                </p>
                """, unsafe_allow_html=True)

                mc_col1, mc_col2 = st.columns(2)
                with mc_col1:
                    n_iterations = st.select_slider(
                        "Nombre d'itérations",
                        options=[100, 500, 1000, 2000, 5000, 10000],
                        value=1000,
                        key="mc_iterations"
                    )
                with mc_col2:
                    mc_sigma = st.slider(
                        "Écart-type σ (points)",
                        min_value=0.5,
                        max_value=5.0,
                        value=2.0,
                        step=0.5,
                        key="mc_sigma",
                        help="Amplitude des perturbations aléatoires sur les scores"
                    )

                if st.button("Lancer la simulation", type="primary", key="mc_run"):
                    # Récupérer les scores actuels depuis T1 ou T2
                    if "votes_t2" in st.session_state and st.session_state.get("listes_t2"):
                        # Utiliser les scores T2
                        sim_votes = st.session_state["votes_t2"]
                        total_v = sum(sim_votes.values())
                        sim_scores = {k: v / total_v * 100 for k, v in sim_votes.items()}
                    elif "r1" in st.session_state:
                        # Utiliser les scores T1
                        sim_scores = st.session_state["r1"].percentages
                    else:
                        sim_scores = None

                    if sim_scores:
                        with st.spinner(f"Simulation en cours ({n_iterations} itérations)..."):
                            mc_results = run_monte_carlo_ui(sim_scores, n_iterations, mc_sigma)
                            st.session_state["mc_results"] = mc_results

                # Afficher les résultats s'ils existent
                if "mc_results" in st.session_state:
                    mc_results = st.session_state["mc_results"]
                    meta = mc_results.get("_meta", {})

                    st.markdown('<div style="height: 16px"></div>', unsafe_allow_html=True)

                    # Statistiques globales
                    p_maj = meta.get("p_majority", 0) * 100
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 12px; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: rgba(255,255,255,0.7);">Probabilité d'une majorité absolue</span>
                            <span style="font-size: 24px; font-weight: 600; color: {'#22c55e' if p_maj > 50 else '#ef4444'};">{p_maj:.1f}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Tableau des intervalles de confiance
                    st.markdown("**Intervalles de confiance (95%)**")

                    mc_data = []
                    for liste, stats in mc_results.items():
                        if liste == "_meta":
                            continue
                        mc_data.append({
                            "Liste": liste.split()[-1] if " " in liste else liste,
                            "Moyenne": f"{stats['mean']:.1f}",
                            "Écart-type": f"{stats['std']:.1f}",
                            "IC 95%": f"[{stats['ci_low']:.0f} - {stats['ci_high']:.0f}]",
                        })

                    # Trier par moyenne décroissante
                    mc_data.sort(key=lambda x: -float(x["Moyenne"]))
                    st.dataframe(pd.DataFrame(mc_data), hide_index=True, use_container_width=True)

                    # Histogramme ECharts des distributions
                    st.markdown('<div style="height: 16px"></div>', unsafe_allow_html=True)
                    st.markdown("**Distribution des sièges (médiane et IC 95%)**")

                    # Préparer les données
                    box_data = []
                    for liste, stats in mc_results.items():
                        if liste == "_meta":
                            continue
                        box_data.append({
                            "name": liste.split()[-1] if " " in liste else liste,
                            "full_name": liste,
                            "median": stats["median"],
                            "ci_low": stats["ci_low"],
                            "ci_high": stats["ci_high"],
                            "mean": stats["mean"],
                            "color": get_color(familles_t1.get(liste, "DIV"))
                        })

                    # Trier par médiane décroissante
                    box_data.sort(key=lambda x: -x["median"])
                    categories = [d["name"] for d in box_data]

                    # Créer le graphique ECharts avec barres d'erreur
                    mc_option = {
                        "tooltip": {
                            "trigger": "axis",
                            "axisPointer": {"type": "shadow"},
                            "formatter": """function(params) {
                                var data = params[0];
                                return data.name + '<br/>Médiane: ' + data.value + ' sièges';
                            }"""
                        },
                        "grid": {
                            "left": "18%",
                            "right": "12%",
                            "top": "8%",
                            "bottom": "12%"
                        },
                        "xAxis": {
                            "type": "value",
                            "name": "Sièges",
                            "nameLocation": "middle",
                            "nameGap": 30,
                            "min": 0,
                            "max": CONSEIL_PARIS_SEATS + 5,
                            "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                            "axisLabel": {"color": "rgba(255,255,255,0.7)"},
                            "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}}
                        },
                        "yAxis": {
                            "type": "category",
                            "data": categories,
                            "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                            "axisLabel": {"color": "rgba(255,255,255,0.9)", "fontSize": 12}
                        },
                        "series": [
                            {
                                "name": "Médiane",
                                "type": "bar",
                                "data": [
                                    {
                                        "value": d["median"],
                                        "itemStyle": {"color": d["color"]}
                                    }
                                    for d in box_data
                                ],
                                "label": {
                                    "show": True,
                                    "position": "right",
                                    "formatter": "{c}",
                                    "color": "rgba(255,255,255,0.8)",
                                    "fontSize": 11
                                },
                                "barWidth": "55%",
                                "markLine": {
                                    "symbol": "none",
                                    "data": [
                                        {
                                            "xAxis": MAYOR_ABSOLUTE_MAJORITY,
                                            "lineStyle": {"color": "#E74C3C", "type": "dashed", "width": 2},
                                            "label": {
                                                "formatter": f"Majorité ({MAYOR_ABSOLUTE_MAJORITY})",
                                                "color": "#E74C3C",
                                                "fontSize": 10
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "name": "IC bas",
                                "type": "scatter",
                                "symbol": "triangle",
                                "symbolSize": 8,
                                "data": [[d["ci_low"], i] for i, d in enumerate(box_data)],
                                "itemStyle": {"color": "rgba(255,255,255,0.6)"},
                                "tooltip": {"show": False}
                            },
                            {
                                "name": "IC haut",
                                "type": "scatter",
                                "symbol": "triangle",
                                "symbolSize": 8,
                                "symbolRotate": 180,
                                "data": [[d["ci_high"], i] for i, d in enumerate(box_data)],
                                "itemStyle": {"color": "rgba(255,255,255,0.6)"},
                                "tooltip": {"show": False}
                            }
                        ]
                    }

                    st_echarts(options=mc_option, height="350px")

                    # Légende
                    st.markdown(f"""
                    <p style="color: rgba(255,255,255,0.5); font-size: 11px; text-align: center; margin-top: 8px;">
                        Barres = médiane · Ligne rouge = majorité ({MAYOR_ABSOLUTE_MAJORITY} sièges) ·
                        {meta.get('n_iterations', 0):,} itérations
                    </p>
                    """, unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================

st.markdown('<div style="height: 60px"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.4); font-size: 12px;">
    paris_elections · Algorithme D'Hondt · Prime majoritaire 25%
</div>
""", unsafe_allow_html=True)
