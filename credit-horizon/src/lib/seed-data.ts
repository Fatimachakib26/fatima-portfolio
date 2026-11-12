// Données issues du rapport académique EMSI « Crédit Horizon » (cas fictif).
// Toutes les lignes insérées à partir de ce fichier sont marquées is_demo = true
// et affichées avec le badge « Démo » dans l'interface.

export const SEED_RISKS = [
  {
    id: "R01",
    title: "Octroi sur dossier incomplet ou incohérent",
    category: "Crédit",
    event:
      "Un crédit est autorisé et décaissé alors que des pièces obligatoires manquent ou que les informations du dossier se contredisent (identité, activité, revenus, garanties).",
    causes:
      "Directes : pièces incomplètes (fait du cas) ; informations incohérentes (fait du cas). Indirectes : pression sur les délais ; absence de liste de pièces obligatoires opposable (hypothèse à vérifier).",
    consequences:
      "Pertes sur créances ; impossibilité de mobiliser des garanties ; difficulté de recouvrement ; observations de l'audit ou du superviseur ; atteinte à la réputation.",
    probability: 5,
    gravity: 3,
    justification:
      "P=5 : le défaut de complétude figure parmi les faits du cas, il est donc déjà observé. G=3 : impact limité par dossier mais cumulatif ; il devient plus lourd si les dossiers concernés sont de montant élevé (à vérifier).",
    owner: "Directeur des risques (contrôle) ; Directeur commercial (constitution)",
    control_ids: "C01, C04",
    coso_principles: "P10, P12, P13",
    basis: "Constat",
    recommendation:
      "Checklist obligatoire des pièces ; blocage du dossier tant qu'une pièce obligatoire manque ; conservation de la preuve du contrôle (C01).",
  },
  {
    id: "R02",
    title: "Décisions d'octroi selon des critères non harmonisés",
    category: "Crédit",
    event:
      "Des dossiers comparables reçoivent des décisions différentes selon le décideur ou l'agence, sans grille commune d'acceptation.",
    causes:
      "Directes : critères non harmonisés (fait du cas). Indirectes : politique de crédit non formalisée ou non diffusée ; absence de comité de crédit structuré (hypothèse à vérifier).",
    consequences:
      "Sélection adverse ; portefeuille hétérogène et difficile à piloter ; contestations de clients ; impossibilité d'expliquer une décision à l'audit.",
    probability: 4,
    gravity: 3,
    justification:
      "P=4 : l'hétérogénéité est un fait du cas, mais sa fréquence exacte est inconnue. G=3 : effet progressif sur la qualité du portefeuille, sans choc immédiat.",
    owner: "Directeur général (politique) ; Directeur des risques (grille d'analyse)",
    control_ids: "C02, C06",
    coso_principles: "P7, P10, P12",
    basis: "Constat",
    recommendation:
      "Grille d'analyse commune et critères documentés ; revue indépendante des décisions dérogatoires (C02, C06).",
  },
  {
    id: "R03",
    title: "Dégradation du portefeuille sous pression des volumes",
    category: "Crédit",
    event:
      "Des objectifs de production fondés sur le volume conduisent à accepter des dossiers plus risqués ; la qualité du portefeuille se dégrade avec un décalage dans le temps.",
    causes:
      "Directes : objectifs de volumes en tension avec la qualité (fait du cas). Indirectes : rémunération ou évaluation des commerciaux sans composante qualité (hypothèse à vérifier) ; croissance sans suivi de la répartition des expositions (hypothèse à vérifier) ; arbitrage direction non formalisé.",
    consequences:
      "Hausse des impayés à moyen terme ; provisions et pertes ; tension sur la rentabilité ; effet de levier négatif sur la croissance recherchée.",
    probability: 4,
    gravity: 5,
    justification:
      "P=4 : la tension volume/qualité est un fait du cas et les incitations jouent dans le sens du volume. G=5 : atteinte potentielle à la viabilité de la stratégie de croissance et à la liquidité par effet de cascade.",
    owner: "Directeur général",
    control_ids: "C02, C03, C06, C07",
    coso_principles: "P5, P6",
    basis: "Constat",
    recommendation:
      "Intégrer un critère de qualité aux objectifs commerciaux ; revue trimestrielle ; suivi de la concentration (C06, C07).",
  },
  {
    id: "R04",
    title: "Retards de remboursement détectés tardivement",
    category: "Crédit",
    event:
      "Des échéances impayées ne sont pas repérées ou escaladées à temps ; le traitement amiable intervient trop tard.",
    causes:
      "Directes : suivi des anomalies insuffisamment formalisé (fait du cas), pouvant retarder la détection des échéances impayées. Indirectes : absence de calendrier d'alertes ; responsabilités de relance mal réparties (hypothèses à vérifier).",
    consequences:
      "Hausse des créances en souffrance ; coûts de recouvrement ; moindre efficacité des garanties ; tension de trésorerie.",
    probability: 3,
    gravity: 3,
    justification:
      "P=3 : le cas établit un suivi des anomalies insuffisamment formalisé, indice indirect de faiblesse du suivi, sans préciser que des retards ont déjà été détectés tardivement. G=3 : impact croissant avec la durée du retard.",
    owner: "Directeur financier",
    control_ids: "C05",
    coso_principles: "P13, P14, P16, P17",
    basis: "Hypothèse",
    recommendation:
      "État périodique des échéances et retards ; chaque alerte attribuée à un responsable et suivie jusqu'à résolution (C05).",
  },
  {
    id: "R05",
    title: "Tension de trésorerie liée à l'accélération des décaissements",
    category: "Liquidité",
    event:
      "La cadence des décaissements dépasse les encaissements et les ressources disponibles, sans anticipation par la fonction finance.",
    causes:
      "Directes : volonté d'accélérer les décisions pour augmenter les volumes (fait du cas). Indirectes : absence de lien entre plan de production et plan de trésorerie (hypothèse à vérifier).",
    consequences:
      "Recours à des financements d'urgence plus coûteux ; report ou gel de décaissements ; dégradation de la relation client ; image de fragilité.",
    probability: 3,
    gravity: 4,
    justification:
      "P=3 : la croissance recherchée accroît l'exposition mais aucune donnée de trésorerie n'est fournie. G=4 : une rupture de liquidité affecte l'ensemble de l'activité.",
    owner: "Directeur financier",
    control_ids: "C05, C08",
    coso_principles: "P7, P13, P14",
    basis: "Hypothèse",
    recommendation:
      "Prévision glissante de trésorerie ; seuil d'escalade interne validé par la direction après analyse des flux (C05, C08).",
  },
  {
    id: "R06",
    title: "Inadéquation entre échéances des crédits et ressources",
    category: "Liquidité",
    event:
      "Les crédits accordés ont des échéances plus longues que les ressources mobilisées, créant un besoin de refinancement récurrent.",
    causes:
      "Directes : développement du financement sans cadrage des ressources (hypothèse à vérifier). Indirectes : concentration des sources de refinancement (hypothèse à vérifier).",
    consequences:
      "Dépendance à un nombre limité de financeurs ; coût de refinancement accru ; contrainte sur la capacité de croissance.",
    probability: 2,
    gravity: 5,
    justification:
      "P=2 : situation non établie par le cas, retenue comme risque structurel de la croissance. G=5 : une impasse de refinancement pourrait interrompre l'activité.",
    owner: "Directeur financier ; Direction générale",
    control_ids: "C05",
    coso_principles: "P7, P13, P14",
    basis: "Hypothèse",
    recommendation:
      "Tableau périodique des échéances des crédits et des ressources mobilisées ; identification des écarts de maturité et des sources de refinancement concentrées ; écarts significatifs soumis à la direction (C05).",
  },
  {
    id: "R07",
    title: "Décision hors délégation ou contournement du circuit d'autorisation",
    category: "Opérationnel",
    event:
      "Un crédit est autorisé par une personne ou une instance non habilitée, ou le même collaborateur constitue, analyse et valide un dossier.",
    causes:
      "Directes : responsabilités d'autorisation imprécises (fait du cas). Indirectes : absence de matrice de délégation signée ; conflit d'intérêts lié aux objectifs commerciaux.",
    consequences:
      "Décisions non opposables ; exposition à la fraude interne ; anomalies relevées par l'audit ; responsabilité des dirigeants engagée.",
    probability: 4,
    gravity: 4,
    justification:
      "P=4 : l'imprécision des responsabilités est un fait du cas. G=4 : le contournement atteint à la fois le risque de crédit, la conformité et la réputation.",
    owner: "Directeur général (délégations) ; Directeur des risques (contrôle)",
    control_ids: "C02, C03",
    coso_principles: "P3, P5",
    basis: "Constat",
    recommendation:
      "Matrice des délégations signée ; contrôle de l'habilitation avant validation ; interdiction de décaisser sans décision valide (C02, C03).",
  },
  {
    id: "R08",
    title: "Anomalies non remontées et données du dossier de mauvaise qualité",
    category: "Opérationnel",
    event:
      "Des anomalies relevées sur les dossiers ne sont ni tracées ni escaladées ; les mêmes erreurs se répètent.",
    causes:
      "Directes : suivi des anomalies insuffisamment formalisé et informations incohérentes (faits du cas). Indirectes : absence d'outil de registre ; absence de culture de remontée (hypothèse à vérifier).",
    consequences:
      "Impossibilité de mesurer les dérives ; décisions de direction fondées sur des données peu fiables ; réponses tardives aux alertes.",
    probability: 4,
    gravity: 3,
    justification:
      "P=4 : la formalisation insuffisante est un fait du cas. G=3 : pas de perte directe, mais effet multiplicateur sur les autres risques.",
    owner: "Directeur des risques",
    control_ids: "C01, C04, C08",
    coso_principles: "P13, P16, P17",
    basis: "Constat",
    recommendation:
      "Registre central des anomalies avec cause, criticité, responsable, échéance, preuve et validation de clôture ; contrôle du reporting avant diffusion (C04, C08).",
  },
];

export const SEED_CONTROLS = [
  {
    id: "C01",
    name: "Contrôle de complétude des dossiers",
    nature: "Préventif",
    objective: "Empêcher qu'un dossier incomplet ou incohérent n'atteigne la décision.",
    risk_ids: "R01, R08",
    procedure:
      "Liste de pièces obligatoires par type de crédit. Le chargé d'affaires coche la liste ; un analyste de la fonction risques, distinct, vérifie les pièces et la cohérence des données avant l'analyse de risque. Le dossier incomplet est retourné avec motif.",
    owner: "Analyste de la fonction risques",
    supervision: "Directeur des risques",
    frequency: "À chaque dossier, avant l'avis de risque",
    evidence: "Liste de contrôle signée et datée ; motif de retour tracé.",
    indicator: "Part des dossiers complets à la première présentation (cible à fixer par la direction) ; nombre de retours par motif.",
    anomaly_treatment: "Retour du dossier ; inscription au registre des anomalies (C04) ; escalade au Directeur commercial si répétition.",
    status: "En déploiement",
  },
  {
    id: "C02",
    name: "Double validation des décisions de crédit",
    nature: "Préventif",
    objective: "Éviter une décision prise par une seule personne et garantir le respect des délégations.",
    risk_ids: "R02, R03, R07",
    procedure:
      "Toute décision requiert deux validations indépendantes selon la matrice de délégation : avis de la fonction risques, puis autorisation par l'instance délégataire (direction ou comité de crédit). Un avis défavorable des risques impose un niveau supérieur et une motivation écrite.",
    owner: "Instance délégataire (direction générale ou comité de crédit)",
    supervision: "Directeur général",
    frequency: "À chaque décision",
    evidence: "Procès-verbal ou fiche de décision signée avec avis risques joint.",
    indicator: "Part des décisions conformes à la délégation ; nombre d'avis défavorables outrepassés.",
    anomaly_treatment: "Décision suspendue ; décaissement bloqué ; remontée à la direction générale.",
    status: "À concevoir",
  },
  {
    id: "C03",
    name: "Séparation des fonctions commerciales, de risques et d'autorisation",
    nature: "Préventif",
    objective: "Empêcher qu'un même collaborateur constitue, analyse et autorise un crédit.",
    risk_ids: "R03, R07",
    procedure:
      "Droits d'accès à l'outil de gestion des dossiers définis par rôle selon la matrice RACI. Le chargé d'affaires n'a pas de droit d'avis ni d'autorisation. Revue semestrielle des droits d'accès.",
    owner: "Direction générale (attribution des rôles) ; Contrôle interne (revue)",
    supervision: "Directeur général",
    frequency: "À l'attribution des droits ; revue semestrielle",
    evidence: "Tableau des droits par rôle ; compte rendu de revue des droits.",
    indicator: "Nombre de cumuls de rôles détectés lors de la revue.",
    anomaly_treatment: "Retrait immédiat des droits cumulés ; analyse des décisions concernées ; rapport à la direction.",
    status: "En déploiement",
  },
  {
    id: "C04",
    name: "Suivi des anomalies et des dérogations",
    nature: "Détectif et correctif",
    objective: "Tracer chaque anomalie et chaque dérogation, et en assurer la correction.",
    risk_ids: "R01, R08",
    procedure:
      "Registre unique des anomalies et dérogations (date, dossier, nature, auteur, motif, décision, échéance de régularisation). Toute dérogation est motivée et validée au niveau de la délégation. Point mensuel de revue du registre par la fonction risques.",
    owner: "Fonction risques (tenue du registre)",
    supervision: "Directeur général",
    frequency: "Tenue continue ; revue mensuelle",
    evidence: "Registre à jour ; compte rendu de la revue mensuelle.",
    indicator: "Anomalies ouvertes par ancienneté ; part de dérogations régularisées dans le délai.",
    anomaly_treatment: "Escalade à la direction générale au-delà du délai fixé ; plan d'action avec responsable.",
    status: "Opérationnel",
  },
  {
    id: "C05",
    name: "Surveillance des retards et de la liquidité",
    nature: "Détectif",
    objective: "Repérer tôt les impayés et les tensions de trésorerie.",
    risk_ids: "R04, R05, R06",
    procedure:
      "La fonction finance produit un état des échéances impayées par ancienneté et un plan de trésorerie prévisionnel confronté au calendrier des décaissements. Un seuil d'alerte qualitatif est défini dans la charte ; son dépassement déclenche une revue de la direction.",
    owner: "Fonction finance",
    supervision: "Directeur général",
    frequency: "Hebdomadaire pour les retards ; mensuelle pour la liquidité",
    evidence: "État des retards daté ; plan de trésorerie validé.",
    indicator: "Dossiers en retard par tranche d'ancienneté ; adéquation décaissements prévus / ressources.",
    anomaly_treatment: "Alerte à la direction ; ajustement ou gel des décaissements ; relance renforcée.",
    status: "À concevoir",
  },
  {
    id: "C06",
    name: "Revue périodique de la qualité du portefeuille",
    nature: "Détectif et correctif",
    objective: "Vérifier que la croissance ne se fait pas au détriment de la qualité du portefeuille.",
    risk_ids: "R02, R03",
    procedure:
      "Chaque trimestre, la fonction risques présente à la direction l'évolution de la qualité par segment, l'origine des dossiers dérogatoires et le respect de la charte. La direction arbitre entre croissance et prudence et le consigne.",
    owner: "Fonction risques",
    supervision: "Direction générale",
    frequency: "Trimestrielle",
    evidence: "Rapport trimestriel ; procès-verbal d'arbitrage.",
    indicator: "Indicateurs qualitatifs de la charte ; respect des délégations ; ancienneté des anomalies.",
    anomaly_treatment: "Plan correctif (resserrement des critères, révision des objectifs commerciaux).",
    status: "À concevoir",
  },
  {
    id: "C07",
    name: "Suivi de la concentration du portefeuille",
    nature: "Détectif",
    objective: "Repérer une exposition excessive à un secteur, une activité, une zone ou une catégorie de clientèle.",
    risk_ids: "R03",
    procedure:
      "La fonction risques ventile les expositions par secteur, activité, zone et catégorie de clientèle, commente toute concentration et propose des mesures de réduction. Les limites éventuelles sont fixées par la direction après analyse de données réelles.",
    owner: "Fonction risques",
    supervision: "Direction générale",
    frequency: "Mensuelle dans le dispositif cible",
    evidence: "Tableau de concentration commenté.",
    indicator: "Part des expositions par segment (seuils à définir après collecte de données réelles).",
    anomaly_treatment: "Analyse renforcée ; proposition de limites ou de mesures de réduction à la direction.",
    status: "À concevoir",
  },
  {
    id: "C08",
    name: "Contrôle du reporting",
    nature: "Détectif",
    objective: "Garantir que la direction décide sur des informations cohérentes, complètes et à jour.",
    risk_ids: "R05, R08",
    procedure:
      "Avant diffusion à la direction, la fonction finance vérifie la cohérence et l'exhaustivité des données, réalise les rapprochements entre échéanciers, encaissements et trésorerie, et valide le reporting.",
    owner: "Fonction finance",
    supervision: "Direction générale",
    frequency: "À chaque clôture de reporting",
    evidence: "Reporting validé ; rapprochements ; journal des corrections.",
    indicator: "Anomalies de reporting détectées ; respect des délais de transmission.",
    anomaly_treatment: "Correction, documentation de l'écart et diffusion d'une version rectifiée.",
    status: "En déploiement",
  },
];

export const SEED_COSO_COMPONENTS = [
  {
    id: 1,
    name: "Environnement de contrôle",
    principles: "P1 à P5",
    question: "Les rôles, l'éthique et les responsabilités sont-ils explicités ?",
    findings:
      "Constat certain : les responsabilités d'autorisation sont imprécises. Constat certain : les objectifs de volume sont en tension avec la qualité. Appréciation provisoire : environnement insuffisant sur la clarté des rôles.",
    gaps:
      "Délégations non précisées ; absence d'arbitrage formalisé entre volume et prudence ; risque de conflit d'intérêts commercial (hypothèse à vérifier).",
    risk_ids: "R03, R07",
    recommendations:
      "Matrice de délégation signée par la direction générale ; charte d'appétence ; objectifs commerciaux intégrant un critère de qualité ; matrice RACI.",
    owner: "Direction générale",
    indicators: "Nombre d'autorisations hors délégation ; part des objectifs commerciaux intégrant un critère de qualité.",
    maturity: 2,
  },
  {
    id: 2,
    name: "Évaluation des risques",
    principles: "P6 à P9",
    question: "Les risques sont-ils identifiés et hiérarchisés ?",
    findings:
      "Constat certain : objectifs de volume et qualité en tension. Hypothèse à vérifier : absence de cartographie documentée. Appréciation provisoire : évaluation partielle, non structurée.",
    gaps:
      "Pas de hiérarchisation commune des risques ; pas de revue des risques lors du changement de stratégie de croissance (hypothèse à vérifier).",
    risk_ids: "R01, R02, R03, R05, R06",
    recommendations:
      "Registre des risques P×G mis à jour chaque trimestre ; revue des risques avant toute révision des objectifs commerciaux.",
    owner: "Fonction risques",
    indicators: "Date de dernière mise à jour du registre ; nombre de risques réévalués par trimestre.",
    maturity: 2,
  },
  {
    id: 3,
    name: "Activités de contrôle",
    principles: "P10 à P12",
    question: "Quelles validations, vérifications et séparations des tâches existent ?",
    findings:
      "Constat certain : pièces incomplètes ; décisions selon des critères non harmonisés. Appréciation provisoire : activités de contrôle insuffisantes à l'octroi.",
    gaps:
      "Pas de contrôle de complétude indépendant ; pas de double validation ; traçabilité des décisions non établie (hypothèse à vérifier).",
    risk_ids: "R01, R02, R07",
    recommendations:
      "Contrôles C01 à C03 ; grille d'acceptation commune ; décision tracée avec identité du décideur et motif.",
    owner: "Fonction risques ; Direction générale",
    indicators: "Part des dossiers complets au premier contrôle ; part des décisions conformes.",
    maturity: 1,
  },
  {
    id: 4,
    name: "Information et communication",
    principles: "P13 à P15",
    question: "L'information et les alertes circulent-elles efficacement ?",
    findings:
      "Constat certain : informations incohérentes ; suivi des anomalies insuffisamment formalisé. Appréciation provisoire : circulation de l'information défaillante.",
    gaps:
      "Données de dossier non fiabilisées ; pas de canal d'alerte formalisé ; reporting à la direction non structuré (hypothèse à vérifier).",
    risk_ids: "R04, R08",
    recommendations:
      "Registre des anomalies ; tableau de bord mensuel des indicateurs ; canal d'escalade défini dans la charte.",
    owner: "Fonction risques ; Fonction finance",
    indicators: "Respect des délais de reporting ; anomalies de reporting détectées.",
    maturity: 2,
  },
  {
    id: 5,
    name: "Pilotage et surveillance",
    principles: "P16 à P17",
    question: "Les anomalies donnent-elles lieu à un suivi et à une amélioration ?",
    findings:
      "Constat certain : suivi des anomalies insuffisamment formalisé. Appréciation provisoire : surveillance principalement réactive.",
    gaps: "Pas de plan correctif suivi ; pas de revue de l'efficacité des contrôles (hypothèse à vérifier).",
    risk_ids: "R04, R08",
    recommendations:
      "Plan d'action daté avec responsable ; suivi des recommandations par la direction générale ; revue annuelle de la charte et des contrôles.",
    owner: "Direction générale ; Contrôle interne",
    indicators: "Taux de clôture des anomalies dans les délais ; taux d'avancement du plan d'action.",
    maturity: 1,
  },
];

export const SEED_COSO_PRINCIPLES = [
  { id: "P1", component_id: 1, title: "Démontre un engagement envers l'intégrité et les valeurs éthiques", nature: "Hypothèse à vérifier", diagnostic: "Code d'éthique et règles de conflits d'intérêts existants ? La pression sur les volumes accroît l'enjeu.", risk_ids: "R03, R07", assessment: "Non évalué" },
  { id: "P2", component_id: 1, title: "Exerce une surveillance de la part de l'organe de gouvernance", nature: "Hypothèse à vérifier", diagnostic: "Surveillance du dispositif par l'organe compétent, selon le statut juridique de l'organisme.", risk_ids: "", assessment: "Non évalué" },
  { id: "P3", component_id: 1, title: "Établit structures, lignes hiérarchiques, pouvoirs et responsabilités", nature: "Constat", diagnostic: "Responsabilités d'autorisation imprécises : structure et pouvoirs non établis.", risk_ids: "R07", assessment: "Déficient" },
  { id: "P4", component_id: 1, title: "Démontre un engagement envers la compétence", nature: "Hypothèse à vérifier", diagnostic: "Compétence des chargés d'affaires en constitution de dossier et formation à la qualité documentaire.", risk_ids: "R01", assessment: "Non évalué" },
  { id: "P5", component_id: 1, title: "Impose la responsabilité de chacun", nature: "Constat et hypothèse", diagnostic: "Constat : tension volume/qualité. Hypothèse : performance mesurée sans critère de qualité, donc responsabilisation déséquilibrée.", risk_ids: "R03, R07", assessment: "Déficient" },
  { id: "P6", component_id: 2, title: "Définit des objectifs adaptés", nature: "Constat", diagnostic: "Objectifs de volume en tension avec la qualité du portefeuille : objectifs non alignés.", risk_ids: "R03", assessment: "Déficient" },
  { id: "P7", component_id: 2, title: "Identifie et analyse les risques", nature: "Constat", diagnostic: "Critères de décision non harmonisés. Hypothèse : cartographie des risques inexistante.", risk_ids: "R02, R05, R06", assessment: "Partiel" },
  { id: "P8", component_id: 2, title: "Évalue le risque de fraude", nature: "Hypothèse à vérifier", diagnostic: "Risque de fraude (dossiers falsifiés, collusion) non évalué.", risk_ids: "R01, R07", assessment: "Non évalué" },
  { id: "P9", component_id: 2, title: "Identifie et analyse les changements importants", nature: "Hypothèse à vérifier", diagnostic: "Effets de la croissance (volumes, nouveaux produits) sur les risques non analysés.", risk_ids: "R03, R05", assessment: "Non évalué" },
  { id: "P10", component_id: 3, title: "Sélectionne et développe des activités de contrôle", nature: "Constat", diagnostic: "Dossiers incomplets : contrôles à l'octroi insuffisants.", risk_ids: "R01, R02", assessment: "Déficient" },
  { id: "P11", component_id: 3, title: "Sélectionne et développe des contrôles généraux sur la technologie", nature: "Hypothèse à vérifier", diagnostic: "Droits d'accès et traçabilité dans l'outil de gestion des dossiers.", risk_ids: "R07", assessment: "Non évalué" },
  { id: "P12", component_id: 3, title: "Déploie par des politiques et des procédures", nature: "Constat", diagnostic: "Critères non harmonisés : procédures non déployées ou non appliquées de façon homogène.", risk_ids: "R01, R02", assessment: "Déficient" },
  { id: "P13", component_id: 4, title: "Utilise des informations pertinentes et de qualité", nature: "Constat", diagnostic: "Informations incohérentes : qualité de l'information non assurée.", risk_ids: "R01, R08", assessment: "Déficient" },
  { id: "P14", component_id: 4, title: "Communique en interne", nature: "Hypothèse à vérifier", diagnostic: "Circuit d'alerte entre commercial, finance, risques et direction.", risk_ids: "R04, R05, R06", assessment: "Non évalué" },
  { id: "P15", component_id: 4, title: "Communique avec l'externe", nature: "Hypothèse à vérifier", diagnostic: "Communication externe (clients, financeurs, autorités) selon le statut.", risk_ids: "", assessment: "Non évalué" },
  { id: "P16", component_id: 5, title: "Effectue des évaluations continues et/ou ponctuelles", nature: "Constat", diagnostic: "Suivi des anomalies insuffisamment formalisé : évaluations continues faibles.", risk_ids: "R04, R08", assessment: "Déficient" },
  { id: "P17", component_id: 5, title: "Évalue et communique les déficiences", nature: "Constat et hypothèse", diagnostic: "Constat : formalisation insuffisante. Hypothèse : pas de plan correctif suivi jusqu'à clôture.", risk_ids: "R04, R08", assessment: "Partiel" },
];

// Chaînes de recommandations (section 5.4) : RISQUE → LACUNE COSO → ACTION → RESPONSABLE → INDICATEUR
export const SEED_RECOMMENDATIONS = [
  { id: "REC01", risk_id: "R01", coso_gap: "Activités de contrôle (P10, P12) : contrôle de complétude et application de la procédure insuffisants (constat).", action: "Checklist obligatoire des pièces ; blocage du dossier tant qu'une pièce obligatoire manque ; conservation de la preuve du contrôle (C01).", owner: "Chargé d'affaires pour la collecte ; analyste de la fonction risques pour le contrôle.", indicator: "Part des dossiers complets au premier contrôle ; dossiers bloqués puis régularisés.", basis: "Constat", status: "En cours" },
  { id: "REC02", risk_id: "R02", coso_gap: "Évaluation des risques (P7) et activités de contrôle (P10, P12) : critères non harmonisés (constat).", action: "Grille d'analyse commune et critères documentés ; revue indépendante des décisions dérogatoires (C02, C06).", owner: "Fonction risques ; validation par la direction ou le comité habilité.", indicator: "Part des décisions documentées ; nombre de dérogations ; écarts relevés en revue.", basis: "Constat", status: "À lancer" },
  { id: "REC03", risk_id: "R03", coso_gap: "Environnement de contrôle (P5) et évaluation des risques (P6) : objectifs de volume en tension avec la qualité (constat).", action: "Intégrer un critère de qualité aux objectifs commerciaux ; revue trimestrielle ; suivi de la concentration (C06, C07).", owner: "Direction générale ; fonction risques pour les indicateurs.", indicator: "Indicateurs qualitatifs de la charte ; part des dérogations ; concentration par segment.", basis: "Constat", status: "À lancer" },
  { id: "REC04", risk_id: "R07", coso_gap: "Environnement de contrôle (P3, P5) : responsabilités d'autorisation imprécises (constat).", action: "Matrice des délégations signée ; contrôle de l'habilitation avant validation ; interdiction de décaisser sans décision valide (C02, C03).", owner: "Direction générale ; la fonction finance vérifie la preuve avant décaissement.", indicator: "Nombre d'autorisations hors délégation ; part des dossiers avec preuve d'autorisation.", basis: "Constat", status: "En cours" },
  { id: "REC05", risk_id: "R04", coso_gap: "Information et communication (P13, P14) et pilotage (P16, P17) : circuit d'alerte à formaliser (hypothèse).", action: "État périodique des échéances et retards ; chaque alerte attribuée à un responsable et suivie jusqu'à résolution (C05).", owner: "Fonction finance pour la détection ; fonction risques pour la surveillance.", indicator: "Dossiers en retard et ancienneté ; délai entre échéance et alerte ; alertes traitées.", basis: "Hypothèse", status: "À lancer" },
  { id: "REC06", risk_id: "R08", coso_gap: "Pilotage et surveillance (P16, P17) et information (P13) : suivi insuffisamment formalisé, informations incohérentes (constats).", action: "Registre central des anomalies avec cause, criticité, responsable, échéance, preuve et validation de clôture ; contrôle du reporting avant diffusion (C04, C08).", owner: "Fonction risques pour le registre ; fonction finance pour le reporting ; direction pour la priorisation.", indicator: "Anomalies clôturées dans les délais ; taux de récurrence ; anomalies de reporting.", basis: "Constat", status: "En cours" },
  { id: "REC07", risk_id: "R05", coso_gap: "Évaluation des risques (P7) et information (P13, P14) : prévision et reporting de liquidité à structurer (hypothèse).", action: "Prévision glissante de trésorerie ; seuil d'escalade interne validé par la direction après analyse des flux (C05, C08).", owner: "Fonction finance ; direction générale en supervision.", indicator: "Écart prévision/réalisé ; nombre d'alertes ; engagements à échéance couverts.", basis: "Hypothèse", status: "À lancer" },
  { id: "REC08", risk_id: "R06", coso_gap: "Évaluation des risques (P7) et information et communication (P13, P14) : adéquation entre échéances des crédits et ressources, et concentration des sources de refinancement, à vérifier (hypothèse).", action: "Tableau périodique des échéances des crédits et des ressources mobilisées ; identification des écarts de maturité et des sources de refinancement concentrées ; écarts significatifs soumis à la direction (C05).", owner: "Fonction finance ; supervision par la direction générale.", indicator: "Revue mensuelle des écarts de maturité ; plan d'action en cas de tension ; part des ressources issues du principal financeur (seuil à fixer par la direction).", basis: "Hypothèse", status: "À lancer" },
];

// Plan d'action (tableau 5.14) – avancement fictif pour la démonstration
export const SEED_ACTIONS = [
  { id: "A01", priority: "P1", title: "Formaliser les délégations et désigner le décideur habilité", owner: "Direction générale", due: "Semaines 1 à 2", deliverable: "Matrice des pouvoirs validée", risk_ids: "R07", control_ids: "C02, C03", status: "En cours", progress: 60 },
  { id: "A02", priority: "P1", title: "Créer la checklist des pièces obligatoires (C01)", owner: "Commercial et risques", due: "Semaines 1 à 2", deliverable: "Checklist et preuve de contrôle", risk_ids: "R01, R08", control_ids: "C01", status: "Terminé", progress: 100 },
  { id: "A03", priority: "P1", title: "Formaliser la double validation et la preuve de décision (C02, C03)", owner: "Direction et risques", due: "Semaines 2 à 3", deliverable: "Procédure d'autorisation ; droits d'accès par rôle", risk_ids: "R02, R03, R07", control_ids: "C02, C03", status: "En cours", progress: 40 },
  { id: "A04", priority: "P1", title: "Ouvrir le registre des anomalies et dérogations (C04)", owner: "Fonction risques", due: "Semaines 2 à 3", deliverable: "Registre et règles d'escalade", risk_ids: "R01, R08", control_ids: "C04", status: "Terminé", progress: 100 },
  { id: "A05", priority: "P2", title: "Adopter la grille commune d'analyse des dossiers", owner: "Fonction risques", due: "Semaines 3 à 5", deliverable: "Grille d'analyse validée", risk_ids: "R02", control_ids: "C02, C06", status: "À faire", progress: 0 },
  { id: "A06", priority: "P2", title: "Mettre en place le suivi des retards et la prévision de trésorerie (C05)", owner: "Fonction finance", due: "Semaines 3 à 6", deliverable: "État des échéances ; prévision glissante", risk_ids: "R04, R05, R06", control_ids: "C05", status: "À faire", progress: 0 },
  { id: "A07", priority: "P2", title: "Mettre en place le suivi de la concentration (C07)", owner: "Fonction risques", due: "Semaines 5 à 7", deliverable: "Tableau de concentration", risk_ids: "R03", control_ids: "C07", status: "À faire", progress: 0 },
  { id: "A08", priority: "P3", title: "Produire le tableau de bord risques et contrôle ; contrôler le reporting (C08)", owner: "Risques et finance", due: "Semaines 7 à 9", deliverable: "Reporting validé", risk_ids: "R05, R08", control_ids: "C08", status: "À faire", progress: 0 },
  { id: "A09", priority: "P3", title: "Faire approuver la charte d'appétence et sensibiliser les équipes", owner: "Direction générale", due: "Semaines 9 à 10", deliverable: "Charte et preuve de sensibilisation", risk_ids: "R03, R07", control_ids: "", status: "À faire", progress: 0 },
  { id: "A10", priority: "P3", title: "Évaluer l'exécution et l'efficacité des contrôles", owner: "Contrôle interne / audit", due: "Semaines 10 à 12", deliverable: "Rapport de revue et plan d'amélioration", risk_ids: "", control_ids: "C01, C02, C03, C04, C05, C06, C07, C08", status: "À faire", progress: 0 },
];

// Anomalies de démonstration (fictives, illustratives des dysfonctionnements D1 à D5)
export const SEED_ANOMALIES = [
  { id: "AN-001", detected_on: "2026-09-08", dossier_ref: "TPE-2026-014", nature: "Pièce manquante : justificatifs de revenus absents lors de la présentation en décision", severity: "Majeure", risk_id: "R01", control_id: "C01", owner: "Fonction risques", due_on: "2026-09-22", status: "Clôturée", escalation: 1, resolution: "Dossier retourné au chargé d'affaires ; pièces régularisées le 2026-09-15." },
  { id: "AN-002", detected_on: "2026-09-19", dossier_ref: "TPE-2026-021", nature: "Incohérence entre le chiffre d'affaires déclaré et les relevés bancaires", severity: "Majeure", risk_id: "R01", control_id: "C01", owner: "Fonction risques", due_on: "2026-10-03", status: "En cours", escalation: 2, resolution: "" },
  { id: "AN-003", detected_on: "2026-10-02", dossier_ref: "TPE-2026-027", nature: "Décision signée par un collaborateur sans délégation formelle", severity: "Critique", risk_id: "R07", control_id: "C02", owner: "Direction générale", due_on: "2026-10-09", status: "Ouverte", escalation: 3, resolution: "" },
  { id: "AN-004", detected_on: "2026-10-11", dossier_ref: "TPE-2026-030", nature: "Dérogation accordée sans motivation écrite tracée", severity: "Significative", risk_id: "R02", control_id: "C04", owner: "Fonction risques", due_on: "2026-10-25", status: "Ouverte", escalation: 1, resolution: "" },
  { id: "AN-005", detected_on: "2026-10-20", dossier_ref: "Reporting sept. 2026", nature: "Écart non expliqué entre l'échéancier et les encaissements du reporting mensuel", severity: "Significative", risk_id: "R08", control_id: "C08", owner: "Fonction finance", due_on: "2026-11-05", status: "En cours", escalation: 2, resolution: "" },
  { id: "AN-006", detected_on: "2026-10-28", dossier_ref: "TPE-2026-009", nature: "Échéance impayée de 45 jours non escaladée", severity: "Majeure", risk_id: "R04", control_id: "C05", owner: "Fonction finance", due_on: "2026-11-10", status: "Ouverte", escalation: 2, resolution: "" },
];

// Historique de cotation (démonstration) pour la courbe « Évolution des risques ».
// Trajectoire illustrative : registre initial (juin) → cotation du rapport (novembre).
export const SEED_HISTORY_MONTHS = ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"];
export const SEED_HISTORY: Record<string, [number, number][]> = {
  R01: [[5, 4], [5, 4], [5, 3], [5, 3], [5, 3], [5, 3]],
  R02: [[4, 3], [4, 3], [4, 3], [4, 3], [4, 3], [4, 3]],
  R03: [[4, 5], [4, 5], [4, 5], [4, 5], [4, 5], [4, 5]],
  R04: [[3, 3], [3, 3], [3, 3], [3, 3], [3, 3], [3, 3]],
  R05: [[3, 3], [3, 3], [3, 4], [3, 4], [3, 4], [3, 4]],
  R06: [[2, 5], [2, 5], [2, 5], [2, 5], [2, 5], [2, 5]],
  R07: [[5, 4], [5, 4], [5, 4], [4, 4], [4, 4], [4, 4]],
  R08: [[5, 3], [5, 3], [4, 3], [4, 3], [4, 3], [4, 3]],
};

export const DEMO_USERS = [
  { email: "admin@credithorizon.ma", name: "Administrateur Démo", role: "admin" },
  { email: "directeur@credithorizon.ma", name: "Directeur Général (démo)", role: "directeur" },
  { email: "analyste@credithorizon.ma", name: "Analyste Risques (démo)", role: "analyste" },
  { email: "commercial@credithorizon.ma", name: "Chargé d'affaires (démo)", role: "commercial" },
  { email: "controleur@credithorizon.ma", name: "Contrôleur Interne (démo)", role: "controleur" },
] as const;

export const DEMO_PASSWORD = "Horizon2026!";
