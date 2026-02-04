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
import altair as alt
import plotly.graph_objects as go

from paris_elections.engine.round1 import run_round1
from paris_elections.engine.round2 import run_round2
from paris_elections.config import (
    CONSEIL_PARIS_SEATS,
    CONSEIL_PARIS_BONUS_FRACTION,
    MAYOR_ABSOLUTE_MAJORITY,
)

# =============================================================================
# PAGE CONFIG & CUSTOM CSS
# =============================================================================

st.set_page_config(
    page_title="Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for modern look (dark mode compatible)
st.markdown("""
<style>
    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* CSS Variables for theming */
    :root {
        --text-primary: rgba(255, 255, 255, 0.95);
        --text-secondary: rgba(255, 255, 255, 0.6);
        --bg-card: rgba(255, 255, 255, 0.05);
        --bg-card-hover: rgba(255, 255, 255, 0.08);
        --border-color: rgba(255, 255, 255, 0.1);
        --accent: #6366f1;
        --accent-light: #818cf8;
    }

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(255, 255, 255, 0.05);
        padding: 8px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.7);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--accent);
        color: white !important;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        text-align: center;
    }

    .metric-card h3 {
        font-size: 14px;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 8px;
    }

    .metric-card h1 {
        font-size: 36px;
        font-weight: 700;
        margin: 0;
    }

    /* Section headers */
    .section-header {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Candidate row */
    .candidate-row {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        margin-bottom: 8px;
    }

    .candidate-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 12px;
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    .badge-success { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
    .badge-warning { background: rgba(234, 179, 8, 0.2); color: #facc15; }
    .badge-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    .badge-info { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }

    /* Progress bar */
    .progress-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        height: 8px;
        overflow: hidden;
    }

    .progress-bar {
        height: 100%;
        border-radius: 8px;
        transition: width 0.3s ease;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 12px;
        padding: 12px 32px;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    }

    /* Input styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    /* Slider */
    .stSlider > div > div > div {
        background: var(--accent);
    }

    /* Divider */
    .divider {
        height: 1px;
        background: rgba(255, 255, 255, 0.1);
        margin: 32px 0;
    }

    /* Info box dark mode */
    .info-box {
        background: rgba(255, 255, 255, 0.05);
        border-left: 4px solid var(--accent);
        padding: 16px 20px;
        border-radius: 0 12px 12px 0;
        margin-bottom: 24px;
    }

    .info-box-label {
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9);
    }

    .info-box-value {
        color: rgba(255, 255, 255, 0.6);
    }

    /* Coalition cards */
    .coalition-success {
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 8px;
        color: #4ade80;
    }

    /* Results analysis items */
    .analysis-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.9);
    }

    .analysis-value {
        font-weight: 600;
    }

    .analysis-pct {
        color: rgba(255, 255, 255, 0.5);
        font-weight: 400;
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
# HEADER
# =============================================================================

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; padding: 40px 0 20px 0;">
        <h1 style="font-size: 42px; font-weight: 700; margin-bottom: 8px; color: rgba(255,255,255,0.95);">
            Municipales Paris 2026
        </h1>
        <p style="font-size: 16px; color: rgba(255,255,255,0.5); font-weight: 400;">
            Simulateur électoral · Conseil de Paris · 163 sièges
        </p>
    </div>
    """, unsafe_allow_html=True)

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

    # Graphique d'évolution des sondages
    with st.expander("📊 Évolution des sondages (nov. 2025 → fév. 2026)", expanded=False):
        # Préparer les données
        evolution_data = []
        for sondage_name, sondage_info in SONDAGES.items():
            if sondage_info["date"]:  # Exclure "Personnalisé"
                for liste in sondage_info["listes"]:
                    evolution_data.append({
                        "Date": sondage_info["date"],
                        "Candidat": liste["nom"],
                        "Score": liste["score"],
                        "Famille": liste["famille"],
                        "Institut": sondage_info["institut"],
                    })

        if evolution_data:
            evo_df = pd.DataFrame(evolution_data)
            evo_df["Date"] = pd.to_datetime(evo_df["Date"])
            evo_df = evo_df.sort_values("Date")

            # Mapping couleurs par candidat
            color_map = {row["Candidat"]: get_color(row["Famille"])
                        for _, row in evo_df.drop_duplicates("Candidat").iterrows()}

            # Trier les candidats par dernier score
            last_scores = evo_df.sort_values("Date").groupby("Candidat").last()["Score"].sort_values(ascending=False)
            sorted_candidates = last_scores.index.tolist()

            # Thème sombre pour Altair
            alt.themes.enable('dark')

            # Seuil de qualification (ligne horizontale)
            threshold_line = alt.Chart(pd.DataFrame({'y': [10]})).mark_rule(
                color='#ef4444',
                strokeWidth=2,
                strokeDash=[8, 4],
                opacity=0.6
            ).encode(y='y:Q')

            threshold_text = alt.Chart(pd.DataFrame({'y': [10], 'text': ['Seuil 10%']})).mark_text(
                align='left',
                dx=5,
                dy=-8,
                fontSize=11,
                color='#ef4444',
                opacity=0.7
            ).encode(
                y='y:Q',
                text='text:N'
            )

            # Lignes principales
            lines = alt.Chart(evo_df).mark_line(
                strokeWidth=3,
                opacity=0.9
            ).encode(
                x=alt.X('Date:T',
                    axis=alt.Axis(
                        format='%d %b',
                        labelAngle=-45,
                        labelColor='#999',
                        titleColor='#666',
                        gridColor='#333',
                        domainColor='#444',
                        title=None
                    )
                ),
                y=alt.Y('Score:Q',
                    scale=alt.Scale(domain=[0, 40]),
                    axis=alt.Axis(
                        labelColor='#999',
                        titleColor='#666',
                        gridColor='#333',
                        domainColor='#444',
                        title='Intentions de vote (%)',
                        format='.0f'
                    )
                ),
                color=alt.Color('Candidat:N',
                    scale=alt.Scale(
                        domain=sorted_candidates,
                        range=[color_map[c] for c in sorted_candidates]
                    ),
                    legend=alt.Legend(
                        title=None,
                        orient='top',
                        columns=3,
                        labelColor='#ccc',
                        labelFontSize=11
                    )
                ),
                strokeDash=alt.StrokeDash('Candidat:N',
                    scale=alt.Scale(
                        domain=sorted_candidates,
                        range=[[1,0], [1,0], [1,0], [4,4], [4,4], [2,2], [2,2]]
                    ),
                    legend=None
                )
            )

            # Points
            points = alt.Chart(evo_df).mark_circle(
                size=80,
                opacity=0.9
            ).encode(
                x='Date:T',
                y='Score:Q',
                color=alt.Color('Candidat:N', legend=None,
                    scale=alt.Scale(
                        domain=sorted_candidates,
                        range=[color_map[c] for c in sorted_candidates]
                    )
                ),
                tooltip=[
                    alt.Tooltip('Candidat:N', title='Candidat'),
                    alt.Tooltip('Score:Q', title='Score', format='.1f'),
                    alt.Tooltip('Date:T', title='Date', format='%d %B %Y'),
                    alt.Tooltip('Institut:N', title='Institut')
                ]
            )

            # Labels sur le dernier point
            last_points = evo_df.sort_values('Date').groupby('Candidat').last().reset_index()

            labels = alt.Chart(last_points).mark_text(
                align='left',
                dx=8,
                fontSize=12,
                fontWeight='bold'
            ).encode(
                x='Date:T',
                y='Score:Q',
                text=alt.Text('Score:Q', format='.0f'),
                color=alt.Color('Candidat:N', legend=None,
                    scale=alt.Scale(
                        domain=sorted_candidates,
                        range=[color_map[c] for c in sorted_candidates]
                    )
                )
            )

            # Combiner
            chart = (threshold_line + threshold_text + lines + points + labels).properties(
                height=380,
            ).configure(
                background='transparent'
            ).configure_view(
                strokeWidth=0
            )

            st.altair_chart(chart, use_container_width=True)

            # Sources
            st.caption("Sources : IFOP-Fiducial, ELABE, Cluster17")

    st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.markdown('<p class="section-header">Candidats</p>', unsafe_allow_html=True)

        familles_options = list(COLORS.keys())
        listes_updated = []

        for i, liste in enumerate(st.session_state["listes"]):
            with st.container():
                cols = st.columns([3, 2, 2, 1.5, 0.5])

                with cols[0]:
                    nom = st.text_input(
                        "Candidat", value=liste["nom"],
                        key=f"nom_{i}", label_visibility="collapsed",
                        placeholder="Nom du candidat"
                    )

                with cols[1]:
                    parti = st.text_input(
                        "Parti", value=liste.get("parti", ""),
                        key=f"parti_{i}", label_visibility="collapsed",
                        placeholder="Parti"
                    )

                with cols[2]:
                    famille = st.selectbox(
                        "Famille", options=familles_options,
                        index=familles_options.index(liste["famille"]) if liste["famille"] in familles_options else 0,
                        key=f"famille_{i}", label_visibility="collapsed"
                    )

                with cols[3]:
                    score = st.number_input(
                        "Score", min_value=0.0, max_value=60.0,
                        value=float(liste["score"]), step=0.5,
                        key=f"score_{i}", label_visibility="collapsed"
                    )

                with cols[4]:
                    if st.button("✕", key=f"del_{i}", help="Supprimer"):
                        st.session_state["listes"].pop(i)
                        st.rerun()

                listes_updated.append({"nom": nom, "parti": parti, "famille": famille, "score": score})

        st.session_state["listes"] = listes_updated

        # Add button
        if st.button("+ Ajouter un candidat", use_container_width=True):
            st.session_state["listes"].append({
                "nom": "", "parti": "", "famille": "DIV", "score": 5.0
            })
            st.rerun()

    with col_side:
        st.markdown('<p class="section-header">Paramètres</p>', unsafe_allow_html=True)

        total = sum(l["score"] for l in st.session_state["listes"])

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

    # Simulate button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        simulate_t1 = st.button("Simuler le 1er tour →", type="primary", use_container_width=True)

    if simulate_t1:
        inscrits = 1_400_000
        exprimes = int(inscrits * participation_t1)
        total = sum(l["score"] for l in st.session_state["listes"])

        votes_t1 = {}
        familles_t1 = {}
        for l in st.session_state["listes"]:
            votes_t1[l["nom"]] = int(l["score"] / total * exprimes) if total > 0 else 0
            familles_t1[l["nom"]] = l["famille"]

        r1 = run_round1(votes_t1, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)

        st.session_state["r1"] = r1
        st.session_state["votes_t1"] = votes_t1
        st.session_state["familles_t1"] = familles_t1
        st.session_state["participation_t1"] = participation_t1
        st.session_state["inscrits"] = inscrits

        st.success("Premier tour simulé")

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

    if "r1" not in st.session_state:
        st.info("Simulez d'abord le premier tour")
    elif st.session_state["r1"].resolved:
        st.info("L'élection a été décidée au premier tour")
    else:
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
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        color = get_color(familles_t1.get(liste, "DIV"))
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; height: 38px; color: rgba(255,255,255,0.9);">
                            <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                            <span>{liste} ({pct:.0f}%)</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        target = st.selectbox(
                            "→", options=["Ne fusionne pas"] + r1.qualified,
                            key=f"fus_{liste}", label_visibility="collapsed"
                        )
                        if target != "Ne fusionne pas":
                            fusions[liste] = {"target": target, "rate": 0.85}

                st.session_state["fusions"] = fusions
                st.markdown('<div style="height: 24px"></div>', unsafe_allow_html=True)

            # Maintiens / Retraits
            st.markdown('<p class="section-header">Maintien ou retrait</p>', unsafe_allow_html=True)

            maintiens = {}
            desistements = {}

            for liste in r1.qualified:
                pct = r1.percentages[liste] * 100
                color = get_color(familles_t1.get(liste, "DIV"))

                col1, col2, col3 = st.columns([2, 1, 2])

                with col1:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; height: 38px; color: rgba(255,255,255,0.9);">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 10px;"></div>
                        <span style="font-weight: 500;">{liste}</span>
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
                            desistements[liste] = {"beneficiary": benef, "rate": 0.65}
                    else:
                        maintiens[liste] = True

            st.session_state["maintiens"] = maintiens
            st.session_state["desistements"] = desistements

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

# =============================================================================
# FOOTER
# =============================================================================

st.markdown('<div style="height: 60px"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.4); font-size: 12px;">
    paris_elections · Algorithme D'Hondt · Prime majoritaire 25%
</div>
""", unsafe_allow_html=True)
