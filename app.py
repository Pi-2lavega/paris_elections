"""
Streamlit Frontend — Simulation Municipales Paris 2026
=======================================================

Flux complet : T1 → Configuration alliances → T2 → Résultats
Listes et scores entièrement personnalisables.

Usage:
    streamlit run app.py
"""

import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from paris_elections.engine.simulation import ElectionSimulator
from paris_elections.engine.round1 import run_round1
from paris_elections.engine.round2 import run_round2
from paris_elections.engine.allocation import allocate_with_bonus
from paris_elections.scenarios.scenario import Scenario
from paris_elections.scenarios.montecarlo import run_monte_carlo
from paris_elections.config import (
    CONSEIL_PARIS_SEATS,
    CONSEIL_PARIS_BONUS_FRACTION,
    MAYOR_ABSOLUTE_MAJORITY,
    POLITICAL_FAMILIES,
    SEUIL_QUALIFICATION_T2,
    SEUIL_FUSION,
    SEUIL_PROPORTIONNELLE,
    DEFAULT_TRANSFER_RATE,
)

# Page config
st.set_page_config(
    page_title="Simulation Municipales Paris 2026",
    page_icon="🗳️",
    layout="wide",
)

# ============================================================================
# COULEURS PAR FAMILLE POLITIQUE
# ============================================================================

COLORS = {
    "EXG": "#8B0000",
    "LFI": "#CC2443",
    "PCF": "#DD0000",
    "PS": "#FF8080",
    "EELV": "#00C000",
    "DVG": "#FFC0CB",
    "REN": "#FFEB00",
    "MDM": "#FF9900",
    "UDI": "#00BFFF",
    "LR": "#0066CC",
    "DVD": "#74B4E8",
    "RN": "#0D378A",
    "REC": "#1A1A2E",
    "EXD": "#404040",
    "DIV": "#999999",
}


def get_color(famille):
    """Retourne la couleur d'une famille politique."""
    return COLORS.get(famille, "#999999")


# ============================================================================
# APPLICATION
# ============================================================================

st.title("🗳️ Simulation Municipales Paris 2026")
st.markdown("**Réforme 2025** : Conseil de Paris (163 sièges, prime 25%) — Scrutin à deux tours")

# Tabs pour les étapes
tab1, tab2, tab3 = st.tabs([
    "1️⃣ Premier Tour — Listes & Scores",
    "2️⃣ Second Tour — Alliances",
    "3️⃣ Résultats Finals",
])

# ============================================================================
# TAB 1 : PREMIER TOUR - SAISIE DES LISTES
# ============================================================================

with tab1:
    st.header("1️⃣ Définition des listes et scores du Premier Tour")

    st.markdown("""
    Données pré-remplies : **Sondage IFOP-Fiducial février 2026**
    Vous pouvez modifier les noms, scores et ajouter/supprimer des listes.
    """)

    st.info("📊 **Source** : IFOP-Fiducial pour Le Parisien/LCI/Sud Radio — Février 2026")

    # Initialisation des listes dans session_state
    # Données : Sondage IFOP-Fiducial février 2026
    if "listes" not in st.session_state:
        st.session_state["listes"] = [
            {"nom": "Emmanuel Grégoire (Gauche unie)", "famille": "PS", "score": 32.0},
            {"nom": "Rachida Dati (LR)", "famille": "LR", "score": 28.0},
            {"nom": "Pierre-Yves Bournazel (Horizons)", "famille": "REN", "score": 14.0},
            {"nom": "Sophia Chikirou (LFI)", "famille": "LFI", "score": 11.0},
            {"nom": "Sarah Knafo (Reconquête)", "famille": "REC", "score": 9.0},
            {"nom": "Thierry Mariani (RN)", "famille": "RN", "score": 5.0},
        ]

    st.markdown("---")
    st.subheader("📝 Listes candidates")

    # Édition des listes
    familles_options = list(COLORS.keys())

    listes_updated = []

    cols_header = st.columns([3, 2, 2, 1])
    with cols_header[0]:
        st.markdown("**Nom de la liste / Tête de liste**")
    with cols_header[1]:
        st.markdown("**Famille politique**")
    with cols_header[2]:
        st.markdown("**Score T1 (%)**")
    with cols_header[3]:
        st.markdown("**Suppr.**")

    for i, liste in enumerate(st.session_state["listes"]):
        cols = st.columns([3, 2, 2, 1])

        with cols[0]:
            nom = st.text_input(
                "Nom",
                value=liste["nom"],
                key=f"nom_{i}",
                label_visibility="collapsed",
            )

        with cols[1]:
            famille = st.selectbox(
                "Famille",
                options=familles_options,
                index=familles_options.index(liste["famille"]) if liste["famille"] in familles_options else 0,
                key=f"famille_{i}",
                label_visibility="collapsed",
            )

        with cols[2]:
            score = st.number_input(
                "Score",
                min_value=0.0,
                max_value=60.0,
                value=float(liste["score"]),
                step=0.5,
                key=f"score_{i}",
                label_visibility="collapsed",
            )

        with cols[3]:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state["listes"].pop(i)
                st.rerun()

        listes_updated.append({"nom": nom, "famille": famille, "score": score})

    st.session_state["listes"] = listes_updated

    # Ajouter une liste
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("➕ Ajouter une liste"):
            st.session_state["listes"].append({
                "nom": f"Nouvelle liste {len(st.session_state['listes'])+1}",
                "famille": "DIV",
                "score": 5.0,
            })
            st.rerun()

    # Total et validation
    st.markdown("---")

    total_score = sum(l["score"] for l in st.session_state["listes"])

    col1, col2, col3 = st.columns(3)

    with col1:
        if abs(total_score - 100) < 1:
            st.success(f"✅ Total : {total_score:.1f}%")
        else:
            st.warning(f"⚠️ Total : {total_score:.1f}% (devrait être ~100%)")

    with col2:
        participation_t1 = st.slider(
            "Participation T1",
            min_value=25,
            max_value=65,
            value=45,
            format="%d%%",
        ) / 100

    with col3:
        st.metric("Nombre de listes", len(st.session_state["listes"]))

    # Visualisation
    st.markdown("---")
    st.subheader("📊 Visualisation des scores T1")

    if st.session_state["listes"]:
        # Tri par score décroissant
        listes_sorted = sorted(st.session_state["listes"], key=lambda x: -x["score"])

        fig = go.Figure()
        for l in listes_sorted:
            fig.add_trace(go.Bar(
                y=[l["nom"]],
                x=[l["score"]],
                orientation='h',
                marker_color=get_color(l["famille"]),
                name=l["nom"],
                text=f"{l['score']:.1f}%",
                textposition='auto',
            ))

        # Seuils
        fig.add_vline(x=10, line_dash="dash", line_color="green",
                     annotation_text="Qualifié T2 (10%)", annotation_position="top")
        fig.add_vline(x=5, line_dash="dot", line_color="orange",
                     annotation_text="Fusion possible (5%)", annotation_position="bottom")

        fig.update_layout(
            showlegend=False,
            height=max(300, len(listes_sorted) * 50),
            xaxis_title="Score (%)",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Simuler T1
    st.markdown("---")

    if st.button("▶️ Simuler le Premier Tour", type="primary", use_container_width=True):
        if not st.session_state["listes"]:
            st.error("❌ Ajoutez au moins une liste")
        else:
            # Normaliser les scores
            total = sum(l["score"] for l in st.session_state["listes"])

            # Calcul des votes
            inscrits = 1_400_000
            exprimes = int(inscrits * participation_t1)

            votes_t1 = {}
            familles_t1 = {}
            for l in st.session_state["listes"]:
                votes_t1[l["nom"]] = int(l["score"] / total * exprimes) if total > 0 else 0
                familles_t1[l["nom"]] = l["famille"]

            # Run T1
            r1 = run_round1(votes_t1, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)

            # Stocker
            st.session_state["r1"] = r1
            st.session_state["votes_t1"] = votes_t1
            st.session_state["familles_t1"] = familles_t1
            st.session_state["participation_t1"] = participation_t1
            st.session_state["inscrits"] = inscrits

            st.success("✅ Premier tour simulé ! Passez à l'onglet 2️⃣")

    # Afficher résultats T1
    if "r1" in st.session_state:
        r1 = st.session_state["r1"]
        familles_t1 = st.session_state.get("familles_t1", {})

        st.markdown("---")
        st.subheader("📊 Résultats du Premier Tour")

        if r1.resolved:
            st.success(f"🏆 **{r1.winner}** obtient la majorité absolue au T1 !")
            st.balloons()
        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**✅ Qualifiés T2 (≥10%)**")
                for liste in r1.qualified:
                    pct = r1.percentages[liste] * 100
                    color = get_color(familles_t1.get(liste, "DIV"))
                    st.markdown(f"<span style='color:{color}'>●</span> **{liste}**: {pct:.1f}%",
                               unsafe_allow_html=True)

            with col2:
                st.markdown("**🔄 Fusion possible (5-10%)**")
                if r1.fusionable:
                    for liste in r1.fusionable:
                        pct = r1.percentages[liste] * 100
                        color = get_color(familles_t1.get(liste, "DIV"))
                        st.markdown(f"<span style='color:{color}'>●</span> {liste}: {pct:.1f}%",
                                   unsafe_allow_html=True)
                else:
                    st.caption("Aucune")

            with col3:
                st.markdown("**❌ Éliminés (<5%)**")
                if r1.eliminated:
                    for liste in r1.eliminated:
                        pct = r1.percentages[liste] * 100
                        color = get_color(familles_t1.get(liste, "DIV"))
                        st.markdown(f"<span style='color:{color}'>●</span> {liste}: {pct:.1f}%",
                                   unsafe_allow_html=True)
                else:
                    st.caption("Aucune")

# ============================================================================
# TAB 2 : CONFIGURATION T2
# ============================================================================

with tab2:
    st.header("2️⃣ Configuration du Second Tour")

    if "r1" not in st.session_state:
        st.warning("⚠️ Simulez d'abord le Premier Tour (onglet 1️⃣)")
    elif st.session_state["r1"].resolved:
        st.info("🏆 L'élection a été résolue au T1 — Voir les résultats dans l'onglet 3️⃣")
    else:
        r1 = st.session_state["r1"]
        votes_t1 = st.session_state["votes_t1"]
        familles_t1 = st.session_state.get("familles_t1", {})

        st.markdown("""
        Configurez les **fusions** et **désistements** entre les deux tours.
        - Les listes **≥10%** peuvent se maintenir ou se retirer
        - Les listes **5-10%** peuvent fusionner avec une liste qualifiée
        """)

        st.markdown("---")

        # === FUSIONS ===
        st.subheader("🤝 Fusions de listes (5-10%)")

        fusions = {}

        if r1.fusionable:
            for liste in r1.fusionable:
                pct = r1.percentages[liste] * 100
                color = get_color(familles_t1.get(liste, "DIV"))

                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.markdown(f"<span style='color:{color}'>●</span> **{liste}** ({pct:.1f}%)",
                               unsafe_allow_html=True)

                with col2:
                    target = st.selectbox(
                        "Fusionne avec",
                        options=["❌ Ne fusionne pas"] + r1.qualified,
                        key=f"fusion_{liste}",
                    )

                with col3:
                    if target != "❌ Ne fusionne pas":
                        transfer = st.slider(
                            "Report",
                            min_value=50,
                            max_value=95,
                            value=85,
                            format="%d%%",
                            key=f"transfer_fusion_{liste}",
                        )
                        fusions[liste] = {"target": target, "rate": transfer / 100}
        else:
            st.caption("Aucune liste entre 5% et 10%")

        st.markdown("---")

        # === DÉSISTEMENTS ===
        st.subheader("🚪 Maintien ou Désistement des listes qualifiées")

        maintiens = {}
        desistements = {}

        for liste in r1.qualified:
            pct = r1.percentages[liste] * 100
            color = get_color(familles_t1.get(liste, "DIV"))

            col1, col2, col3 = st.columns([2, 1, 2])

            with col1:
                st.markdown(f"<span style='color:{color}'>●</span> **{liste}** ({pct:.1f}%)",
                           unsafe_allow_html=True)

            with col2:
                action = st.radio(
                    "Action",
                    options=["✅ Maintien", "🚪 Retrait"],
                    key=f"action_{liste}",
                    horizontal=True,
                    label_visibility="collapsed",
                )

            with col3:
                if action == "🚪 Retrait":
                    autres = [l for l in r1.qualified if l != liste]
                    if autres:
                        benef = st.selectbox(
                            "Report vers",
                            options=autres,
                            key=f"benef_{liste}",
                        )
                        rate = st.slider(
                            "Taux report",
                            min_value=30,
                            max_value=90,
                            value=65,
                            format="%d%%",
                            key=f"rate_{liste}",
                        )
                        desistements[liste] = {"beneficiary": benef, "rate": rate / 100}
                else:
                    maintiens[liste] = True

        st.markdown("---")

        # === PARTICIPATION T2 ===
        st.subheader("📈 Participation au Second Tour")

        col1, col2 = st.columns(2)

        with col1:
            part_t1 = st.session_state["participation_t1"] * 100
            delta = st.slider(
                "Variation vs T1",
                min_value=-10,
                max_value=+15,
                value=+3,
                format="%+d pts",
            )

        with col2:
            participation_t2 = (part_t1 + delta) / 100
            st.metric("Participation T2", f"{participation_t2*100:.0f}%", f"{delta:+d} pts")

        # Stocker config
        st.session_state["fusions"] = fusions
        st.session_state["desistements"] = desistements
        st.session_state["maintiens"] = maintiens
        st.session_state["participation_t2"] = participation_t2

        st.markdown("---")

        # === RÉCAPITULATIF ===
        st.subheader("📋 Listes présentes au Second Tour")

        # Calculer votes T2
        listes_t2 = [l for l in r1.qualified if l in maintiens]
        votes_t2 = {}

        for liste in listes_t2:
            base = votes_t1[liste]

            # + fusions entrantes
            for src, data in fusions.items():
                if data["target"] == liste:
                    base += int(votes_t1.get(src, 0) * data["rate"])

            # + désistements entrants
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

        # Affichage
        if listes_t2:
            total = sum(votes_t2.values())

            col1, col2 = st.columns(2)

            with col1:
                for liste in sorted(listes_t2, key=lambda x: -votes_t2.get(x, 0)):
                    pct = votes_t2[liste] / total * 100 if total > 0 else 0
                    color = get_color(familles_t1.get(liste, "DIV"))
                    st.markdown(f"<span style='color:{color}'>●</span> **{liste}**: {pct:.1f}%",
                               unsafe_allow_html=True)

            with col2:
                n = len(listes_t2)
                if n == 2:
                    st.info("🥊 **Duel**")
                elif n == 3:
                    st.warning("⚡ **Triangulaire**")
                elif n >= 4:
                    st.error("🔥 **Quadrangulaire+**")

                st.metric("Listes en lice", n)
        else:
            st.error("❌ Aucune liste ne se maintient au T2")

# ============================================================================
# TAB 3 : RÉSULTATS
# ============================================================================

with tab3:
    st.header("3️⃣ Résultats de l'Élection")

    if "r1" not in st.session_state:
        st.warning("⚠️ Simulez d'abord le Premier Tour (onglet 1️⃣)")
        seats = None
    elif st.session_state["r1"].resolved:
        # Résolu au T1
        r1 = st.session_state["r1"]
        seats = r1.seats
        st.success("🏆 **Élection résolue au Premier Tour**")
    elif "votes_t2" not in st.session_state or not st.session_state.get("listes_t2"):
        st.warning("⚠️ Configurez les alliances du Second Tour (onglet 2️⃣)")
        seats = None
    else:
        # Simuler T2
        if st.button("▶️ Simuler le Second Tour", type="primary", use_container_width=True):
            votes_t2 = st.session_state["votes_t2"]
            r2 = run_round2(votes_t2, CONSEIL_PARIS_SEATS, CONSEIL_PARIS_BONUS_FRACTION)
            st.session_state["r2"] = r2
            st.session_state["final_seats"] = r2.seats

        seats = st.session_state.get("final_seats")

        if not seats:
            st.info("👆 Cliquez pour simuler le second tour")

    # Affichage des résultats
    if seats:
        familles_t1 = st.session_state.get("familles_t1", {})

        st.markdown("---")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🏛️ Conseil de Paris — 163 sièges")

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
                        textposition='auto',
                    ))

            fig.add_vline(x=MAYOR_ABSOLUTE_MAJORITY, line_dash="dash", line_color="red",
                         annotation_text=f"Majorité ({MAYOR_ABSOLUTE_MAJORITY})")

            fig.update_layout(
                showlegend=False,
                height=400,
                xaxis_title="Sièges",
                xaxis=dict(range=[0, CONSEIL_PARIS_SEATS + 5]),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📊 Résumé")

            winner = max(seats, key=seats.get)
            winner_seats = seats[winner]

            color = get_color(familles_t1.get(winner, "DIV"))
            st.markdown(f"### <span style='color:{color}'>🏆 {winner}</span>", unsafe_allow_html=True)
            st.metric("Sièges obtenus", f"{winner_seats} / {CONSEIL_PARIS_SEATS}")

            if winner_seats >= MAYOR_ABSOLUTE_MAJORITY:
                st.success("✅ **Majorité absolue !**")
                st.metric("Marge", f"+{winner_seats - MAYOR_ABSOLUTE_MAJORITY}")
            else:
                st.error("❌ **Pas de majorité**")
                st.metric("Déficit", f"-{MAYOR_ABSOLUTE_MAJORITY - winner_seats}")

        # Tableau détaillé
        st.markdown("---")
        st.subheader("📋 Répartition des sièges")

        df = pd.DataFrame([
            {
                "Liste": l,
                "Famille": familles_t1.get(l, "DIV"),
                "Sièges": n,
                "% Conseil": f"{n/CONSEIL_PARIS_SEATS*100:.1f}%",
            }
            for l, n in sorted(seats.items(), key=lambda x: -x[1])
            if n > 0
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Analyse coalitions
        st.markdown("---")
        st.subheader("🤝 Coalitions possibles")

        # Grouper par bloc
        blocs = {"Gauche": 0, "Centre": 0, "Droite": 0, "Ext. Droite": 0, "Autre": 0}

        GAUCHE = ["PS", "LFI", "PCF", "EELV", "DVG", "EXG"]
        CENTRE = ["REN", "MDM", "UDI"]
        DROITE = ["LR", "DVD"]
        EXT_DROITE = ["RN", "REC", "EXD"]

        for liste, n in seats.items():
            fam = familles_t1.get(liste, "DIV")
            if fam in GAUCHE:
                blocs["Gauche"] += n
            elif fam in CENTRE:
                blocs["Centre"] += n
            elif fam in DROITE:
                blocs["Droite"] += n
            elif fam in EXT_DROITE:
                blocs["Ext. Droite"] += n
            else:
                blocs["Autre"] += n

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔴 Gauche", blocs["Gauche"])
        with col2:
            st.metric("🟡 Centre", blocs["Centre"])
        with col3:
            st.metric("🔵 Droite", blocs["Droite"])
        with col4:
            st.metric("⚫ Ext. Droite", blocs["Ext. Droite"])

        # Coalitions
        coalitions = [
            ("Gauche seule", blocs["Gauche"]),
            ("Gauche + Centre", blocs["Gauche"] + blocs["Centre"]),
            ("Droite seule", blocs["Droite"]),
            ("Droite + Centre", blocs["Droite"] + blocs["Centre"]),
            ("Centre seul", blocs["Centre"]),
        ]

        st.markdown("**Majorités possibles (≥82 sièges) :**")
        found = False
        for name, total in coalitions:
            if total >= MAYOR_ABSOLUTE_MAJORITY:
                st.success(f"✅ **{name}** : {total} sièges")
                found = True

        if not found:
            st.warning("⚠️ Aucune coalition simple n'atteint la majorité")

# Footer
st.markdown("---")
st.caption("**paris_elections** — Simulation municipales Paris 2026 | Algorithme D'Hondt | Prime majoritaire 25%")
