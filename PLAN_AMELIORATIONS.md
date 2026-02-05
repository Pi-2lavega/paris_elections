# Plan d'amélioration — Simulateur Municipales Paris 2026

## 1. Données & Sources

### 1.1 Agrégation automatique des sondages
- [ ] Scraper automatique des nouveaux sondages (Commission des sondages)
- [ ] API pour récupérer les derniers sondages en temps réel
- [ ] Pondération des instituts par track record historique
- [ ] Moyenne mobile pondérée (rolling average) des sondages

### 1.2 Données démographiques par secteur
- [ ] Intégrer les données INSEE par arrondissement (CSP, revenus, âge)
- [ ] Corrélations historiques démographie × vote
- [ ] Ajustement des projections par profil socio-démographique du secteur

### 1.3 Historique électoral enrichi
- [ ] Résultats détaillés municipales 2014, 2020 par bureau de vote
- [ ] Présidentielle 2022 T1/T2 par arrondissement
- [ ] Législatives 2022, 2024 pour calibrer les transferts
- [ ] Européennes 2024 comme proxy des rapports de force actuels

---

## 2. Modèles & Précision

### 2.1 Modèle de redressement amélioré
- [ ] Redressement par famille politique (pas global)
- [ ] Prise en compte de l'effet "spiral of silence" (sous-déclaration RN/REC)
- [ ] Correction par mode de collecte (téléphone vs online)
- [ ] Intervalle de confiance dynamique selon la variance historique

### 2.2 Matrice de transfert dynamique
- [ ] Taux de transfert ajustables par l'utilisateur (sliders)
- [ ] Scénarios prédéfinis : "Front républicain", "Bloc contre bloc", "Éclatement"
- [ ] Validation sur les législatives 2024 (données réelles de report)
- [ ] Prise en compte de l'abstention différentielle par famille

### 2.3 Simulation Monte Carlo avancée
- [ ] Corrélation entre erreurs de sondage (pas indépendantes)
- [ ] Distribution non-normale (fat tails pour les surprises)
- [ ] Sensibilité aux hypothèses (tornado chart)
- [ ] Intervalles de crédibilité bayésiens

### 2.4 Modèle de participation
- [ ] Participation différenciée par arrondissement (historique)
- [ ] Impact météo, actualité, mobilisation
- [ ] Effet de la configuration du second tour sur la participation

---

## 3. Fonctionnalités

### 3.1 Simulation des 17 scrutins sectoriels
- [ ] Scores différenciés par arrondissement (pas uniforme)
- [ ] Simulation des conseils d'arrondissement (prime 50%)
- [ ] Maires d'arrondissement projetés
- [ ] Carte interactive des résultats par secteur

### 3.2 Élection du maire
- [ ] Simulation des 3 tours au Conseil de Paris
- [ ] Coalitions et négociations possibles
- [ ] Probabilité d'élection par candidat
- [ ] Scénarios de coalition (gauche+centre, droite+centre, etc.)

### 3.3 Scénarios prédéfinis
- [x] "Gauche unie" : PS+EELV+PCF fusionnent dès le T1
- [x] "Droite unie" : LR+REN alliance
- [x] "Fragmentation maximale" : aucune fusion
- [ ] "Front républicain" : désistements croisés anti-RN/REC
- [ ] Import/export de scénarios (JSON)

### 3.4 Comparaison de scénarios
- [ ] Vue côte à côte de 2-3 scénarios
- [ ] Différences en sièges (delta)
- [ ] Graphique de sensibilité (quel paramètre change le plus le résultat)

---

## 4. Visualisations

### 4.1 Hémicycle interactif
- [x] Diagramme en demi-cercle du Conseil de Paris (163 sièges)
- [x] Coloration par famille politique
- [x] Ligne de majorité (82 sièges)
- [ ] Animation de la répartition

### 4.2 Carte choroplèthe
- [ ] Carte de Paris par arrondissement
- [ ] Couleur = vainqueur ou marge de victoire
- [ ] Tooltip avec détails au survol
- [ ] Comparaison T1/T2 en slider

### 4.3 Sankey des transferts
- [ ] Flux visuels T1 → T2
- [ ] Épaisseur = volume de voix transférées
- [ ] Couleur = famille politique

### 4.4 Graphiques de probabilité
- [ ] Distribution des sièges par liste (histogramme MC)
- [ ] Probabilité de majorité par coalition
- [ ] Intervalle de confiance à 50%, 90%, 95%

---

## 5. UX / Interface

### 5.1 Workflow guidé
- [ ] Stepper visuel : Sondage → T1 → Alliances → T2 → Résultat
- [ ] Validation à chaque étape avant de passer à la suivante
- [ ] Résumé des hypothèses en sidebar permanente

### 5.2 Mode expert vs simplifié
- [ ] Mode simplifié : sliders basiques, scénarios prédéfinis
- [ ] Mode expert : tous les paramètres, matrice de transfert éditable
- [ ] Toggle pour basculer

### 5.3 Responsive design
- [ ] Adaptation mobile/tablette
- [ ] Touch-friendly pour les sliders

### 5.4 Export des résultats
- [ ] Export PDF du rapport de simulation
- [ ] Export PNG des graphiques
- [ ] Partage par lien (état encodé dans l'URL)

---

## 6. Qualité & Robustesse

### 6.1 Tests
- [ ] Tests unitaires pour l'allocation D'Hondt
- [ ] Tests de non-régression sur cas historiques (2020)
- [ ] Tests de la matrice de transfert (somme ≤ 1)
- [ ] Validation croisée du modèle de redressement

### 6.2 Documentation
- [ ] README complet avec screenshots
- [ ] Méthodologie détaillée (PDF)
- [ ] Sources des données citées
- [ ] Limitations et avertissements

### 6.3 Performance
- [ ] Cache des calculs lourds (Monte Carlo)
- [ ] Lazy loading des graphiques
- [ ] Optimisation du re-render Streamlit

---

## 7. Priorités suggérées

### Phase 1 — Court terme (1-2 semaines)
1. Corriger le bug des valeurs qui changent ✅
2. Implémenter la matrice de transfert ✅
3. Ajouter les noms de famille ✅
4. Simulation Monte Carlo accessible depuis l'UI ✅
5. Export PDF basique ✅

### Phase 2 — Moyen terme (1 mois)
1. Carte choroplèthe par arrondissement ✅
2. Hémicycle interactif ✅
3. Scénarios prédéfinis (3-4 scénarios) ✅
4. Mode simplifié vs expert ✅

### Phase 3 — Long terme (2-3 mois)
1. Scraper automatique des sondages
2. Simulation complète des 17 secteurs
3. Élection du maire avec coalitions
4. Application mobile (Streamlit Cloud ou autre)

---

## 8. Stack technique recommandée

| Composant | Actuel | Recommandé |
|-----------|--------|------------|
| Frontend | Streamlit | Streamlit (suffisant) ou Next.js pour plus de contrôle |
| Graphiques | ECharts | ECharts + Plotly pour hémicycle |
| Cartes | — | Folium ou Leaflet.js |
| Backend | Python | Python (FastAPI si besoin d'API) |
| Base de données | — | SQLite ou PostgreSQL pour historique |
| Hébergement | Local | Streamlit Cloud ou Heroku |

---

## 9. Risques et limitations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Sondages peu fiables | Élevé | Afficher les intervalles de confiance, disclaimers |
| Matrice de transfert incertaine | Élevé | Permettre ajustement manuel, Monte Carlo |
| Réforme 2025 mal comprise | Moyen | Vérifier le décret d'application |
| Données sectorielles manquantes | Moyen | Hypothèse d'uniformité avec avertissement |
| Candidatures de dernière minute | Faible | Interface flexible pour ajouter des candidats |

---

*Plan élaboré le 5 février 2026*
