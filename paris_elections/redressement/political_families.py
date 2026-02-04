"""Classification des listes électorales par famille politique.

Mapping curé manuellement par élection : noms de listes → familles.
"""

from __future__ import annotations

from typing import Dict, Optional

from paris_elections.config import POLITICAL_FAMILIES, PoliticalFamily


# ---------------------------------------------------------------------------
# Mappings historiques : nom de liste → code famille
# ---------------------------------------------------------------------------

# Municipales 2020 (Paris, listes principales)
MAPPING_MUNICIPALES_2020: Dict[str, str] = {
    "HIDALGO": "PS",
    "PARIS EN COMMUN": "PS",
    "DATI": "LR",
    "CHANGER PARIS": "LR",
    "BUZYN": "REN",
    "VILLANI": "EELV",
    "BELLIARD": "EELV",
    "SIMONNET": "LFI",
    "BROSSAT": "PCF",
    "BOURNAZEL": "DVD",
    "CAMPION": "DIV",
}

# Présidentielle 2022 T1 (noms candidats → famille)
MAPPING_PRESIDENTIELLE_2022: Dict[str, str] = {
    "ARTHAUD": "EXG",
    "POUTOU": "EXG",
    "ROUSSEL": "PCF",
    "MELENCHON": "LFI",
    "MÉLENCHON": "LFI",
    "JADOT": "EELV",
    "HIDALGO": "PS",
    "MACRON": "REN",
    "PECRESSE": "LR",
    "PÉCRESSE": "LR",
    "LASSALLE": "DIV",
    "ZEMMOUR": "REC",
    "LE PEN": "RN",
    "DUPONT-AIGNAN": "EXD",
}

# Européennes 2024 (têtes de liste / partis → famille)
MAPPING_EUROPEENNES_2024: Dict[str, str] = {
    "BARDELLA": "RN",
    "HAYER": "REN",
    "GLUCKSMANN": "PS",
    "TOUSSAINT": "EELV",
    "AUBRY": "LFI",
    "BELLAMY": "LR",
    "MARÉCHAL": "REC",
    "BOMPARD": "LFI",
}

ALL_MAPPINGS: Dict[str, Dict[str, str]] = {
    "municipales_2020": MAPPING_MUNICIPALES_2020,
    "presidentielle_2022": MAPPING_PRESIDENTIELLE_2022,
    "europeennes_2024": MAPPING_EUROPEENNES_2024,
}


def classify_list(
    list_name: str,
    election: Optional[str] = None,
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Classe une liste dans une famille politique.

    Recherche par correspondance partielle (case-insensitive).

    Args:
        list_name: nom de la liste.
        election: clé d'élection pour utiliser le mapping spécifique.
        custom_mapping: mapping personnalisé (prioritaire).

    Returns:
        Code famille (ex. "PS") ou None si non trouvé.
    """
    name_upper = list_name.upper().strip()

    # Custom mapping en priorité
    if custom_mapping:
        for key, family in custom_mapping.items():
            if key.upper() in name_upper:
                return family

    # Mapping par élection
    if election and election in ALL_MAPPINGS:
        for key, family in ALL_MAPPINGS[election].items():
            if key.upper() in name_upper:
                return family

    # Recherche dans tous les mappings
    for mapping in ALL_MAPPINGS.values():
        for key, family in mapping.items():
            if key.upper() in name_upper:
                return family

    return None


def get_family(code: str) -> Optional[PoliticalFamily]:
    """Retourne la PoliticalFamily pour un code donné."""
    return POLITICAL_FAMILIES.get(code)


def family_color(code: str) -> str:
    """Retourne la couleur associée à une famille politique."""
    f = POLITICAL_FAMILIES.get(code)
    return f.color if f else "#999999"


def classify_scores(
    scores: Dict[str, float],
    election: Optional[str] = None,
) -> Dict[str, Dict[str, float]]:
    """Regroupe les scores par famille politique.

    Args:
        scores: dict liste → score.
        election: clé d'élection pour le mapping.

    Returns:
        dict famille → dict(listes, total_score).
    """
    families: Dict[str, float] = {}
    for list_name, score in scores.items():
        family = classify_list(list_name, election) or "DIV"
        families[family] = families.get(family, 0.0) + score
    return {f: {"score": s} for f, s in families.items()}
