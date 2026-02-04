"""Constantes électorales, secteurs, sièges — municipales Paris 2026.

Réforme d'août 2025 :
  - Scrutin 1 : liste unique parisienne → Conseil de Paris (163 sièges, prime 25%)
  - Scrutin 2 : 17 scrutins sectoriels → conseils d'arrondissement (prime 50%)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Mode électoral
# ---------------------------------------------------------------------------

class ElectionMode(Enum):
    """PRE_2026 = ancien système par arrondissement ; POST_2026 = réforme 2025."""
    PRE_2026 = "pre_2026"
    POST_2026 = "post_2026"


# ---------------------------------------------------------------------------
# Secteurs (post-réforme)
# ---------------------------------------------------------------------------

# 17 secteurs : Paris Centre (1er-4e) + 5e à 20e
SECTEURS: Dict[str, List[int]] = {
    "Paris Centre": [1, 2, 3, 4],
    "5e":  [5],
    "6e":  [6],
    "7e":  [7],
    "8e":  [8],
    "9e":  [9],
    "10e": [10],
    "11e": [11],
    "12e": [12],
    "13e": [13],
    "14e": [14],
    "15e": [15],
    "16e": [16],
    "17e": [17],
    "18e": [18],
    "19e": [19],
    "20e": [20],
}

ARRONDISSEMENT_TO_SECTEUR: Dict[int, str] = {}
for _sect, _arrs in SECTEURS.items():
    for _a in _arrs:
        ARRONDISSEMENT_TO_SECTEUR[_a] = _sect

# Codes commune INSEE (75101..75120)
ARRONDISSEMENT_INSEE: Dict[int, str] = {i: f"751{i:02d}" for i in range(1, 21)}


# ---------------------------------------------------------------------------
# Conseil de Paris — 163 sièges
# ---------------------------------------------------------------------------

CONSEIL_PARIS_SEATS = 163
CONSEIL_PARIS_BONUS_FRACTION = 0.25  # prime majoritaire 25%

# Sièges prime + proportionnelle
CONSEIL_PARIS_BONUS_SEATS = round(CONSEIL_PARIS_SEATS * CONSEIL_PARIS_BONUS_FRACTION)  # 41
CONSEIL_PARIS_PROPORTIONAL_SEATS = CONSEIL_PARIS_SEATS - CONSEIL_PARIS_BONUS_SEATS     # 122


# ---------------------------------------------------------------------------
# Conseils d'arrondissement — sièges par secteur (proportionnels à la pop.)
#
# NOTE : Le décret d'application de la réforme de 2025 n'est peut-être pas
# encore publié. Les valeurs ci-dessous sont des estimations provisionnelles
# basées sur la population légale 2021 et le barème du CGCT art. L2121-2.
# À actualiser dès publication du décret.
# ---------------------------------------------------------------------------

# Barème CGCT : tranches de population → nombre de conseillers municipaux.
# Pour les arrondissements, le nombre de conseillers est fixé par décret.
# Ci-dessous : estimations cohérentes avec les résultats 2020 (pré-réforme)
# et ajustées pour la fusion Paris Centre.

CONSEIL_ARRONDISSEMENT_SEATS: Dict[str, int] = {
    "Paris Centre": 99,   # fusion 1er(11)+2e(11)+3e(15)+4e(15) → total historique ~52 + élargissement
    "5e":  27,
    "6e":  21,
    "7e":  25,
    "8e":  21,
    "9e":  27,
    "10e": 33,
    "11e": 41,
    "12e": 37,
    "13e": 41,
    "14e": 37,
    "15e": 53,
    "16e": 41,
    "17e": 41,
    "18e": 51,
    "19e": 47,
    "20e": 51,
}

# NOTE PROVISOIRE : ces chiffres reproduisent les sièges des conseils
# d'arrondissement en vigueur en 2020. Il est possible que la réforme
# modifie ces effectifs. Un avertissement est émis à l'utilisation.
_SEATS_PROVISIONAL = True

CONSEIL_ARRONDISSEMENT_BONUS_FRACTION = 0.50  # prime majoritaire 50%


# ---------------------------------------------------------------------------
# Seuils légaux
# ---------------------------------------------------------------------------

SEUIL_QUALIFICATION_T2 = 0.10   # 10% des suffrages exprimés → qualifié T2
SEUIL_FUSION = 0.05             # 5-10% → peut fusionner avec une liste qualifiée
SEUIL_PROPORTIONNELLE = 0.05    # 5% des suffrages → participe à la répartition des sièges
SEUIL_VICTOIRE_T1 = 0.50        # > 50% au T1 → élu

# Participation de référence
PARTICIPATION_DEFAUT = 0.45  # Taux moyen aux municipales à Paris


# ---------------------------------------------------------------------------
# Familles politiques
# ---------------------------------------------------------------------------

@dataclass
class PoliticalFamily:
    """Famille politique avec métadonnées de visualisation et redressement."""
    code: str
    label: str
    color: str
    short_label: str = ""
    # Biais historique moyen (en points, sondage - résultat) ; positif = sondage surestime
    historical_bias: float = 0.0
    historical_bias_std: float = 0.0

    def __post_init__(self):
        if not self.short_label:
            self.short_label = self.code


POLITICAL_FAMILIES: Dict[str, PoliticalFamily] = {
    "EXG": PoliticalFamily("EXG", "Extrême gauche", "#8B0000", "Ext. G"),
    "LFI": PoliticalFamily("LFI", "La France Insoumise", "#CC2443", "LFI",
                           historical_bias=1.5, historical_bias_std=1.2),
    "PCF": PoliticalFamily("PCF", "Parti Communiste", "#DD0000", "PCF",
                           historical_bias=0.3, historical_bias_std=0.5),
    "PS":  PoliticalFamily("PS",  "Parti Socialiste", "#FF8080", "PS",
                           historical_bias=-0.5, historical_bias_std=1.0),
    "EELV": PoliticalFamily("EELV", "Ecologistes", "#00C000", "EELV",
                            historical_bias=1.0, historical_bias_std=1.5),
    "DVG": PoliticalFamily("DVG", "Divers gauche", "#FFC0CB", "DVG"),
    "REN": PoliticalFamily("REN", "Renaissance", "#FFEB00", "REN",
                           historical_bias=0.5, historical_bias_std=1.0),
    "MDM": PoliticalFamily("MDM", "MoDem", "#FF9900", "MoDem",
                           historical_bias=0.2, historical_bias_std=0.5),
    "LR":  PoliticalFamily("LR",  "Les Républicains", "#0066CC", "LR",
                           historical_bias=-1.0, historical_bias_std=1.2),
    "DVD": PoliticalFamily("DVD", "Divers droite", "#74B4E8", "DVD"),
    "RN":  PoliticalFamily("RN",  "Rassemblement National", "#0D378A", "RN",
                           historical_bias=-2.0, historical_bias_std=1.5),
    "REC": PoliticalFamily("REC", "Reconquête", "#1A1A2E", "REC",
                           historical_bias=-0.5, historical_bias_std=1.0),
    "EXD": PoliticalFamily("EXD", "Extrême droite", "#404040", "Ext. D"),
    "DIV": PoliticalFamily("DIV", "Divers", "#999999", "Div."),
}

FAMILY_CODES = list(POLITICAL_FAMILIES.keys())


# ---------------------------------------------------------------------------
# Coalitions / alliances typiques
# ---------------------------------------------------------------------------

COALITION_GAUCHE = {"LFI", "PCF", "PS", "EELV", "DVG", "EXG"}
COALITION_CENTRE = {"REN", "MDM"}
COALITION_DROITE = {"LR", "DVD"}
COALITION_EXT_DROITE = {"RN", "REC", "EXD"}


# ---------------------------------------------------------------------------
# Élection du maire : 3 tours possibles
# ---------------------------------------------------------------------------

MAYOR_ROUNDS_MAX = 3
# Tour 1 & 2 : majorité absolue (82/163), Tour 3 : pluralité
MAYOR_ABSOLUTE_MAJORITY = (CONSEIL_PARIS_SEATS // 2) + 1  # 82


# ---------------------------------------------------------------------------
# Transfert de voix par défaut (T1 → T2)
# ---------------------------------------------------------------------------

DEFAULT_TRANSFER_RATE = 0.85

# =============================================================================
# MATRICE DE TRANSFERT DE VOIX (T1 → T2)
# =============================================================================
# Basée sur les études post-électorales (IPSOS, IFOP) des législatives 2024
# et municipales 2020. Les taux représentent la fraction des électeurs
# d'une famille (ligne) qui reportent leur vote vers une autre (colonne).
# Le complément à 100% = abstention différentielle.
#
# Format: TRANSFER_MATRIX[famille_source][famille_cible] = taux

TRANSFER_MATRIX: Dict[str, Dict[str, float]] = {
    # Extrême gauche
    "EXG": {
        "EXG": 0.90, "LFI": 0.85, "PCF": 0.80, "PS": 0.70, "EELV": 0.75,
        "DVG": 0.65, "REN": 0.20, "MDM": 0.15, "UDI": 0.10, "LR": 0.10,
        "DVD": 0.10, "RN": 0.05, "REC": 0.03, "EXD": 0.02, "DIV": 0.30,
    },
    # La France Insoumise
    "LFI": {
        "EXG": 0.70, "LFI": 0.90, "PCF": 0.75, "PS": 0.60, "EELV": 0.65,
        "DVG": 0.50, "REN": 0.15, "MDM": 0.12, "UDI": 0.08, "LR": 0.08,
        "DVD": 0.08, "RN": 0.08, "REC": 0.05, "EXD": 0.03, "DIV": 0.25,
    },
    # Parti Communiste
    "PCF": {
        "EXG": 0.65, "LFI": 0.70, "PCF": 0.90, "PS": 0.75, "EELV": 0.70,
        "DVG": 0.60, "REN": 0.20, "MDM": 0.15, "UDI": 0.10, "LR": 0.10,
        "DVD": 0.10, "RN": 0.05, "REC": 0.03, "EXD": 0.02, "DIV": 0.30,
    },
    # Parti Socialiste
    "PS": {
        "EXG": 0.45, "LFI": 0.55, "PCF": 0.60, "PS": 0.90, "EELV": 0.75,
        "DVG": 0.70, "REN": 0.40, "MDM": 0.35, "UDI": 0.20, "LR": 0.15,
        "DVD": 0.15, "RN": 0.05, "REC": 0.03, "EXD": 0.02, "DIV": 0.35,
    },
    # Europe Écologie Les Verts
    "EELV": {
        "EXG": 0.50, "LFI": 0.60, "PCF": 0.55, "PS": 0.70, "EELV": 0.90,
        "DVG": 0.65, "REN": 0.35, "MDM": 0.30, "UDI": 0.15, "LR": 0.12,
        "DVD": 0.12, "RN": 0.05, "REC": 0.03, "EXD": 0.02, "DIV": 0.35,
    },
    # Divers Gauche
    "DVG": {
        "EXG": 0.40, "LFI": 0.50, "PCF": 0.55, "PS": 0.70, "EELV": 0.65,
        "DVG": 0.85, "REN": 0.40, "MDM": 0.35, "UDI": 0.25, "LR": 0.20,
        "DVD": 0.20, "RN": 0.08, "REC": 0.05, "EXD": 0.03, "DIV": 0.40,
    },
    # Renaissance (Macronistes)
    "REN": {
        "EXG": 0.10, "LFI": 0.12, "PCF": 0.15, "PS": 0.35, "EELV": 0.30,
        "DVG": 0.30, "REN": 0.90, "MDM": 0.85, "UDI": 0.70, "LR": 0.55,
        "DVD": 0.50, "RN": 0.10, "REC": 0.08, "EXD": 0.05, "DIV": 0.40,
    },
    # MoDem
    "MDM": {
        "EXG": 0.08, "LFI": 0.10, "PCF": 0.12, "PS": 0.30, "EELV": 0.28,
        "DVG": 0.28, "REN": 0.85, "MDM": 0.90, "UDI": 0.70, "LR": 0.55,
        "DVD": 0.50, "RN": 0.10, "REC": 0.08, "EXD": 0.05, "DIV": 0.40,
    },
    # UDI
    "UDI": {
        "EXG": 0.05, "LFI": 0.05, "PCF": 0.08, "PS": 0.20, "EELV": 0.18,
        "DVG": 0.18, "REN": 0.65, "MDM": 0.70, "UDI": 0.90, "LR": 0.75,
        "DVD": 0.70, "RN": 0.15, "REC": 0.12, "EXD": 0.08, "DIV": 0.35,
    },
    # Les Républicains
    "LR": {
        "EXG": 0.03, "LFI": 0.05, "PCF": 0.05, "PS": 0.12, "EELV": 0.10,
        "DVG": 0.12, "REN": 0.45, "MDM": 0.50, "UDI": 0.70, "LR": 0.90,
        "DVD": 0.80, "RN": 0.30, "REC": 0.25, "EXD": 0.15, "DIV": 0.30,
    },
    # Divers Droite
    "DVD": {
        "EXG": 0.03, "LFI": 0.05, "PCF": 0.05, "PS": 0.15, "EELV": 0.12,
        "DVG": 0.15, "REN": 0.50, "MDM": 0.50, "UDI": 0.65, "LR": 0.80,
        "DVD": 0.85, "RN": 0.28, "REC": 0.22, "EXD": 0.12, "DIV": 0.35,
    },
    # Rassemblement National
    "RN": {
        "EXG": 0.02, "LFI": 0.08, "PCF": 0.03, "PS": 0.05, "EELV": 0.03,
        "DVG": 0.05, "REN": 0.12, "MDM": 0.10, "UDI": 0.12, "LR": 0.25,
        "DVD": 0.22, "RN": 0.92, "REC": 0.75, "EXD": 0.70, "DIV": 0.15,
    },
    # Reconquête
    "REC": {
        "EXG": 0.01, "LFI": 0.03, "PCF": 0.02, "PS": 0.03, "EELV": 0.02,
        "DVG": 0.03, "REN": 0.15, "MDM": 0.12, "UDI": 0.18, "LR": 0.35,
        "DVD": 0.30, "RN": 0.70, "REC": 0.92, "EXD": 0.75, "DIV": 0.12,
    },
    # Extrême Droite
    "EXD": {
        "EXG": 0.01, "LFI": 0.02, "PCF": 0.01, "PS": 0.02, "EELV": 0.02,
        "DVG": 0.02, "REN": 0.08, "MDM": 0.06, "UDI": 0.10, "LR": 0.20,
        "DVD": 0.18, "RN": 0.75, "REC": 0.80, "EXD": 0.90, "DIV": 0.10,
    },
    # Divers
    "DIV": {
        "EXG": 0.15, "LFI": 0.20, "PCF": 0.18, "PS": 0.30, "EELV": 0.28,
        "DVG": 0.30, "REN": 0.35, "MDM": 0.32, "UDI": 0.30, "LR": 0.30,
        "DVD": 0.28, "RN": 0.15, "REC": 0.12, "EXD": 0.08, "DIV": 0.50,
    },
}


def get_transfer_rate(source_family: str, target_family: str) -> float:
    """Retourne le taux de transfert entre deux familles politiques.

    Args:
        source_family: Famille politique de la liste qui se retire/fusionne.
        target_family: Famille politique de la liste bénéficiaire.

    Returns:
        Taux de transfert (0.0 à 1.0).
    """
    if source_family == target_family:
        return 0.90  # Même famille = fort report

    source_matrix = TRANSFER_MATRIX.get(source_family, TRANSFER_MATRIX.get("DIV", {}))
    return source_matrix.get(target_family, DEFAULT_TRANSFER_RATE * 0.5)


# ---------------------------------------------------------------------------
# Monte Carlo par défaut
# ---------------------------------------------------------------------------

MC_DEFAULT_ITERATIONS = 10_000
MC_SCORE_SIGMA = 0.02          # σ = 2 pts sur les scores
MC_PARTICIPATION_SIGMA = 0.03  # σ = 3 pts sur la participation
MC_TRANSFER_SIGMA = 0.10       # σ = 10% sur les taux de transfert


def warn_provisional_seats():
    """Émet un avertissement si les sièges sont provisionnels."""
    if _SEATS_PROVISIONAL:
        import warnings
        warnings.warn(
            "Les effectifs des conseils d'arrondissement sont provisionnels "
            "(basés sur les données 2020). À actualiser lors de la publication "
            "du décret d'application de la réforme de 2025.",
            UserWarning,
            stacklevel=2,
        )
