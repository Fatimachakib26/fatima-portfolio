const fs = require('fs');
const R = __dirname, S = R + '/..';
const K = JSON.parse(fs.readFileSync(S + '/calc.json'));
const C = JSON.parse(fs.readFileSync(S + '/course.json'));
const FIG = JSON.parse(fs.readFileSync(S + '/docfig.json'));
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType, LevelFormat, BorderStyle, Footer, Header, PageNumber, ImageRun, TabStopType } = require('docx');
const which = process.argv[2], start = Number(process.argv[3]), out = process.argv[4];
const F = 'Liberation Serif', PURPLE = '57369A', DARK = '24233A', INK = '222222', LAV = 'EAE7F2';
const W = 9638;
const fr = (v, d = 2) => v.toFixed(d).replace('.', ',');
const pc = (v, d = 2) => fr(v * 100, d) + ' %';
const mm = (v) => fr(v / 1e6, 2) + ' M';
const n0 = (v) => Math.round(v).toLocaleString('fr-FR').replace(/ | /g, ' ');
const runs = (t, o = {}) => String(t).split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) => s.startsWith('**') ? new TextRun({ text: s.slice(2, -2), bold: true, ...o }) : new TextRun({ text: s, ...o }));
const P = (t, o = {}) => new Paragraph({ children: runs(t, { color: INK }), alignment: AlignmentType.JUSTIFIED, spacing: { after: 140, line: 288 }, ...o });
const H2 = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true, size: 30, color: PURPLE })], spacing: { before: 300, after: 140 }, keepNext: true });
const H3 = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true, size: 25, color: DARK })], spacing: { before: 200, after: 100 }, keepNext: true });
const B = (t) => new Paragraph({ children: runs(t, { color: INK }), numbering: { reference: 'b', level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 70, line: 276 } });
const CAP = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true, size: 19, color: DARK })], spacing: { before: 160, after: 70 }, keepNext: true });
const SRC = (t) => new Paragraph({ children: [new TextRun({ text: t, italics: true, size: 18, color: '555555' })], spacing: { before: 50, after: 160 } });
const bd = { style: BorderStyle.SINGLE, size: 4, color: 'C8C2DA' };
function T(head, rows, widths, num = []) {
  const tot = widths.reduce((a, b) => a + b, 0); widths = widths.map((w) => Math.round(w * W / tot)); widths[widths.length - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, h, r) => new TableCell({ width: { size: widths[i], type: WidthType.DXA }, borders: { top: bd, bottom: bd, left: bd, right: bd },
    shading: h ? { type: ShadingType.CLEAR, fill: PURPLE, color: 'auto' } : r % 2 ? { type: ShadingType.CLEAR, fill: 'F4F2F9', color: 'auto' } : undefined,
    margins: { top: 45, bottom: 45, left: 80, right: 80 },
    children: [new Paragraph({ alignment: num.includes(i) && !h ? AlignmentType.RIGHT : AlignmentType.LEFT, children: runs(String(t), h ? { size: 18, color: 'FFFFFF', bold: true } : { size: 18, color: INK }) })] });
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true, 0)) }), ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, k)) }))] });
}
const NOTE = (t) => new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W], rows: [new TableRow({ children: [new TableCell({ width: { size: W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill: LAV, color: 'auto' }, borders: { top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, left: { style: BorderStyle.SINGLE, size: 24, color: PURPLE } }, margins: { top: 90, bottom: 90, left: 160, right: 140 }, children: [new Paragraph({ children: runs(t, { size: 18, color: INK }), alignment: AlignmentType.JUSTIFIED, spacing: { line: 252 } })] })] })] });
const FIGURE = (i, n, title) => [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 }, children: [new ImageRun({ type: 'png', data: fs.readFileSync(`${S}/docfig-${i}.png`), transformation: { width: 600, height: Math.round(600 * FIG[i].h / FIG[i].w) } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `Figure ${n} – ${title}`, italics: true, size: 19, color: DARK })], spacing: { before: 60, after: 180 } })];
const TITLE = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true, size: 44, color: DARK })], spacing: { after: 240 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: PURPLE, space: 6 } } });
const SEC = (t) => new Paragraph({ children: [new TextRun({ text: t, color: INK, size: 21 })], numbering: { reference: 's', level: 0 }, spacing: { after: 50 } });

const el = K.base, sc = K.scen, ov = K.ov, t = K.t;
const pick = (tb, k, v) => t[tb].find((r) => r[k] === v);
const wpd = el.rows.reduce((a, r) => a + r.pd * r.ead, 0) / el.ead, wlgd = el.rows.reduce((a, r) => a + r.lgd * r.ead, 0) / el.ead;
const RES = { R01: [5, 3, 'Réduire', 2, 3], R02: [4, 3, 'Réduire', 2, 3], R03: [4, 5, 'Réduire et transférer (garanties)', 2, 5], R04: [3, 3, 'Réduire', 2, 3], R05: [3, 4, 'Réduire', 2, 4], R06: [2, 5, 'Réduire et transférer (ressources)', 2, 4], R07: [4, 4, 'Réduire', 1, 4], R08: [4, 3, 'Réduire', 2, 3] };
const CTRL = { R01: 'C01, C04', R02: 'C02, C06', R03: 'C02, C03, C06, C07', R04: 'C05', R05: 'C05, C08', R06: 'C05', R07: 'C02, C03', R08: 'C01, C04, C08' };
const lvl = (s) => (s >= 16 ? 'Critique' : s >= 10 ? 'Élevé' : s >= 5 ? 'Modéré' : 'Faible');

let header, body;
if (which === '6') {
  header = 'Chapitre 6 – Ouverture : mesure du risque de crédit et approfondissements';
  body = [
    TITLE('Chapitre 6 : Ouverture : mesure du risque de crédit et approfondissements du cours'),
    P("Ce chapitre prolonge le dispositif qualitatif des chapitres 1 à 5. Il adopte la posture de l'analyste risque crédit, propose une mesure indicative du risque de crédit (probabilité de défaut, perte en cas de défaut, pertes attendues, provisions et stress test) et approfondit plusieurs notions des cours de gestion des risques financiers et de contrôle interne : typologie et interdépendance des risques, risque inhérent et résiduel, stratégies de traitement."),
    P('Ce chapitre est organisé en sections successives :'),
    ...['6.1 Statut du chapitre et rôle de l\'analyste risque crédit', '6.2 Perte attendue, perte inattendue et provisions', '6.3 Calibration sur des données publiques vérifiées', '6.4 Application à un portefeuille fictif de 500 M MAD', '6.5 Stress test et nature des risques', '6.6 Typologie et interdépendance des risques', '6.7 Risque inhérent, risque résiduel et traitement', '6.8 Limites de la mesure'].map(SEC),
    H2("6.1 Statut du chapitre et rôle de l'analyste risque crédit"),
    NOTE("**Ouverture hors fiche.** La fiche projet demande une charte d'appétence qualitative, sans PD/LGD : les chapitres 1 à 5 respectent cette exigence et l'hypothèse H6 reste valable pour les cotations P × G. Ce chapitre est un prolongement. Il n'utilise aucune donnée réelle de Crédit Horizon : les paramètres proviennent de données publiques externes (section 6.3) et le portefeuille de 500 M MAD est fictif, construit pour la démonstration."),
    new Paragraph({ spacing: { after: 80 } }),
    P("La matrice RACI (section 4.4) confie à la fonction risques un avis indépendant sur l'octroi. Le profil de l'analyste risque crédit précise le contenu de cet avis : il s'agit de **mesurer** le risque, à l'échelle du dossier comme du portefeuille, et de proposer les moyens de le **maîtriser**."),
    CAP("Tableau 6.1 – Profil de l'analyste risque crédit et traduction dans le dispositif"),
    T(['Critère', 'Analyste risque crédit', 'Traduction dans le dispositif'], [
      ['Mission principale', 'Évaluer, mesurer et maîtriser le risque de non-remboursement', 'Registre des risques (4.1), mesure du portefeuille (6.4)'], ['Orientation', 'Maîtrise du risque', "Charte d'appétence (5.1), plan d'action (5.5)"],
      ['Approche', 'Analyse individuelle et globale du portefeuille', 'Grille du dossier (5.3) ; portefeuille (6.4)'], ['Analyse financière', 'Oui, avec un focus sur le risque', 'Ratios du dossier, grille C01 (5.3)'],
      ['Garanties', 'Oui', 'Facteur garantie de la PD et de la LGD'], ['Probabilité de défaut (PD)', 'Oui : outil clé', 'PD calibrée (6.3)'],
      ['Suivi des impayés', 'Oui : suivi rapproché', 'Contrôle C05, risque R04'], ['Analyse du portefeuille', 'Approfondie : concentration, secteurs', 'HHI, trois premiers secteurs, contrôle C07'],
      ['Provisions et pertes attendues', 'Important : modélisation des pertes', 'Provisions IFRS 9 (6.2, 6.4)'], ['Reporting', 'Important : indicateurs de risque', 'Indicateurs de pilotage (5.5), contrôle C08'],
      ['Compétences clés', 'Modèles PD, LGD, EAD ; Bâle II/III, IFRS 9', 'Sections 6.2 à 6.5'], ['Exemple concret', "Mesurer l'impact d'un défaut sur le portefeuille de 500 M et ajuster les provisions", 'Stress test (6.5)']].map(([a, b, c]) => [`**${a}**`, b, c]), [24, 40, 36]),
    SRC("Source : fiche de profil « Analyste risque crédit » ; colonne de droite : élaboration des auteures."),
    P("En résumé, l'analyste risque crédit se demande **« Quel est le risque ? », et comment le maîtriser**. Il éclaire la décision sans la prendre : l'autorisation reste du ressort de l'instance délégataire (contrôle C02)."),
    H2('6.2 Perte attendue, perte inattendue et provisions'),
    P("Le cours de gestion des risques (chapitre 1, section 8) distingue la **perte attendue**, estimation moyenne de la perte associée à une exposition, de la **perte inattendue**, qui dépasse ce niveau en cas de crise, de défauts simultanés ou d'événements extrêmes. Dans une représentation simplifiée du risque de crédit :"),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'EL = PD × LGD × EAD', bold: true, size: 26, color: PURPLE })], spacing: { before: 60, after: 120 } }),
    B("**PD** (probabilité de défaut) : probabilité qu'un emprunteur fasse défaut sur un horizon donné, ici 12 mois."),
    B("**LGD** (perte en cas de défaut) : part de l'exposition perdue après garanties et récupérations."),
    B("**EAD** (exposition au moment du défaut) : l'encours."),
    P("La perte attendue est un coût normal du métier, couvert par les **provisions** ; la perte inattendue doit être absorbée par les **fonds propres**. La norme IFRS 9 organise les provisions en trois stades : stade 1, pertes attendues à 12 mois ; stade 2 (dégradation significative), pertes attendues sur la durée de vie, avec une PD cumulée 1 − (1 − PD)^durée ; stade 3 (défaut), LGD × encours."),
    P("Conformément à l'hypothèse H2, le statut de Crédit Horizon n'est pas connu : Bâle II/III, les textes de Bank Al-Maghrib qui les transposent et IFRS 9 sont utilisés ici comme **bonnes pratiques de mesure**, non comme obligations."),
    ...FIGURE(3, '6.1', 'De la probabilité de défaut aux provisions et aux fonds propres'),
    H2('6.3 Calibration sur des données publiques vérifiées'),
    P(`Faute de données propres (H6), les paramètres sont calibrés sur une source publique et vérifiable : les données « FOIA » du programme 7(a) de la **Small Business Administration** américaine (prêts garantis aux petites entreprises, cohortes ${ov.cohorts}, situation au 30/09/2026, licence U.S. Government Works). Le fichier brut de 545 751 lignes est téléchargé tel quel et son empreinte SHA-256 est enregistrée ; un pipeline Python applique neuf règles de nettoyage numérotées, conserve chaque ligne écartée avec sa règle et vérifie que lignes brutes = lignes retenues + lignes rejetées (544 605 + 1 146). Les données personnelles des emprunteurs sont supprimées.`),
    P("La préparation suit six étapes : **acquisition** (portail officiel, contrôle de la taille, empreinte et manifeste) ; **profilage** (chaque colonne lue en texte, sans conversion) ; **validation et nettoyage** (neuf règles numérotées et comptées, 1 136 doublons exacts et 10 prêts incohérents écartés) ; **minimisation** (nom, adresse et code postal supprimés) ; **agrégation** par cohorte, secteur, montant, durée et garantie ; **contrôle croisé** (taux de défaut recalculé indépendamment). Elle applique à la donnée deux objectifs du contrôle interne : un reporting fiable et la conformité."),
    P(`Sur ${n0(ov.loans_funded)} prêts décaissés, ${n0(ov.loans_resolved)} sont dénoués et ${n0(ov.defaults)} ont été passés en perte. La **PD annuelle** est un taux d'incidence : λ = défauts ÷ années d'exposition (${n0(ov.exposure_years)}), puis PD = 1 − e^(−λ) = **${pc(ov.pd_annual)}**. La **LGD** rapporte le montant passé en perte au montant initial des prêts concernés : **${pc(ov.lgd, 1)}**.`),
    CAP('Tableau 6.2 – PD et LGD de référence selon la garantie et la durée'),
    T(['Segment', 'Prêts', 'Défaut sur la vie du prêt', 'PD 12 mois', 'LGD'], [
      ...[true, false].map((v) => { const r = pick('by_collateral', 'collateral', v); return [v ? 'Avec garantie réelle' : 'Sans garantie réelle', n0(r.loans), pc(r.default_rate), pc(r.pd_annual), pc(r.lgd, 1)]; }),
      ...['≤ 1 an', '1–5 ans', '5–10 ans', '> 10 ans'].map((v) => { const r = pick('by_term', 'term_band', v); return ['Durée ' + v, n0(r.loans), pc(r.default_rate), pc(r.pd_annual), pc(r.lgd, 1)]; }),
      ['**Ensemble**', n0(ov.loans_funded), pc(ov.default_rate), pc(ov.pd_annual), pc(ov.lgd, 1)]], [34, 14, 20, 16, 16], [1, 2, 3, 4]),
    SRC('Source : SBA, 7(a) FOIA FY2010–FY2019 ; calculs des auteures.'),
    P(`Ces repères rejoignent les constats qualitatifs du chapitre 4 : sans garantie réelle, la PD annuelle est supérieure de ${fr((pick('by_collateral', 'collateral', false).pd_annual / pick('by_collateral', 'collateral', true).pd_annual - 1) * 100, 0)} % (intérêt du contrôle C01) ; les crédits courts font défaut plus souvent ; la PD sectorielle va de ${pc(pick('by_sector', 'sector', 'Finance et assurance').pd_annual)} à ${pc(pick('by_sector', 'sector', 'Transport et entreposage').pd_annual)}.`),
    H2('6.4 Application à un portefeuille fictif de 500 M MAD'),
    P("Un portefeuille fictif de 500 M MAD est réparti en neuf segments sectoriels, avec pour chacun une part garantie, une durée moyenne et des parts d'encours en stades 2 et 3. La PD de chaque segment est la PD de référence multipliée par les facteurs relatifs du secteur, de la garantie et de la durée."),
    CAP('Tableau 6.3 – Pertes attendues et provisions IFRS 9 du portefeuille fictif (en M MAD)'),
    T(['Secteur', 'EAD', 'Garanti', 'Durée', 'PD 12 mois', 'LGD', 'EL 12 mois', 'Stades 2/3', 'Provision'],
      [...el.rows.map((r) => [r.sector, mm(r.ead), r.collateral + ' %', r.term + ' m', pc(r.pd), pc(r.lgd, 0), mm(r.el12), `${r.stage2} / ${r.stage3} %`, mm(r.provision)]),
       ['**Total**', mm(el.ead), '', '', pc(wpd), pc(wlgd, 0), mm(el.el12), '', mm(el.provision)]], [27, 9, 8, 8, 10, 7, 10, 11, 10], [1, 2, 3, 4, 5, 6, 8]),
    SRC('Portefeuille fictif ; paramètres SBA ; calculs des auteures.'),
    P(`Les pertes attendues à 12 mois atteignent **${mm(el.el12)} MAD** et les provisions IFRS 9 **${mm(el.provision)} MAD** (${pc(el.coverage)} de l'encours). Environ 60 % des provisions proviennent des encours en stades 2 et 3, qui ne représentent que 11 % de l'encours : le suivi des retards (C05) conditionne directement le provisionnement. Les trois premiers secteurs pèsent ${pc(el.top3, 0)} de l'encours (indice de Herfindahl ${fr(el.hhi, 3)}), contre ${pc(ov.top3_sector_share, 0)} dans le portefeuille SBA : c'est le **risque de concentration** du cours, suivi par C07.`),
    H2('6.5 Stress test et nature des risques'),
    P("L'exemple type de l'analyste risque crédit consiste à « mesurer l'impact d'un défaut sur le portefeuille de 500 M et ajuster les provisions ». Quatre scénarios ont été simulés :"),
    CAP('Tableau 6.4 – Résultats des scénarios de stress (en M MAD)'),
    T(['Scénario', 'Hypothèse', 'Nature du risque', 'Provisions', 'Couverture', 'Dotation supplémentaire'],
      [['Situation de base', '–', '–', mm(el.provision), pc(el.coverage), '–'],
       ...[['Récession modérée', 'PD × 1,5 ; LGD + 5 pts', 'Systématique'], ['Récession sévère', 'PD × 2 ; LGD + 10 pts', 'Systématique'], ['Crise du BTP', 'PD de la construction × 2,5', 'Sectoriel (concentration)'], ['Défaut 5 M MAD', "Défaut d'une contrepartie", 'Spécifique']].map(([k, h, n]) => { const s = sc[k]; return [k, h, n, mm(s.provision), pc(s.coverage), `+${mm(s.provision - el.provision)} (+${fr((s.provision / el.provision - 1) * 100, 0)} %)`]; })],
      [16, 24, 18, 12, 12, 18], [3, 4, 5]),
    SRC('Calculs des auteures.'),
    P(`En récession sévère, les provisions passent de ${mm(el.provision)} à ${mm(sc['Récession sévère'].provision)} MAD : l'écart de ${mm(sc['Récession sévère'].provision - el.provision)} MAD illustre une **perte inattendue**. Une récession est un **risque systématique** : la diversification ne la supprime pas, on la mesure par le stress test. Le défaut d'une seule contrepartie de 5 M MAD est un **risque spécifique**, réductible par la diversification ; il coûte toutefois ${mm(sc['Défaut 5 M MAD'].singleLoss)} MAD, soit ${fr(sc['Défaut 5 M MAD'].singleLoss / el.provision * 100, 0)} % des provisions de base, ce qui plaide pour une limite par contrepartie dans la charte (article 8).`),
    H2('6.6 Typologie et interdépendance des risques'),
    P("Le cours de gestion des risques (chapitre 2) distingue risques de marché (actions, taux, change, matières premières), de crédit (défaut, dégradation, contrepartie, concentration), de liquidité (de marché et de financement) et opérationnel (personnes, processus, systèmes, événements externes). Le tableau 6.5 les rapporte à Crédit Horizon."),
    CAP('Tableau 6.5 – Typologie du cours appliquée à Crédit Horizon'),
    T(['Risque', 'Exposition de Crédit Horizon', 'Niveau', 'Dans le dossier'], C.TYPOLOGY.map((x) => [`**${x.type}**`, x.exposure, x.level, x.where]), [24, 36, 12, 28]),
    SRC('Source : élaboration des auteures à partir du cours de gestion des risques financiers, chapitre 2.'),
    P("Les risques ne sont pas indépendants. Le cours illustre une chaîne taux → marché → crédit → liquidité. Chez Crédit Horizon, l'effet domino part de l'octroi : " + C.CHAIN.map((c) => `${c.id} (${c.text.toLowerCase()})`).join(' → ') + ". Un risque opérationnel et de crédit à l'entrée finit en risque de liquidité, ce qui justifie de traiter R01 et R02 en priorité."),
    H2('6.7 Risque inhérent, risque résiduel et traitement'),
    P("Les cotes P × G du chapitre 4 sont des cotes de **risque inhérent**, avant tout dispositif de maîtrise. Le cours définit le **risque résiduel** comme ce qui subsiste après la mise en place des dispositifs, et quatre stratégies de traitement : éviter, réduire, transférer, accepter. Le tableau 6.6 propose, à titre d'hypothèse, le risque résiduel visé une fois les contrôles du chapitre 5 en service."),
    CAP('Tableau 6.6 – Risque inhérent, traitement et risque résiduel visé'),
    T(['Risque', 'Inhérent (P × G)', 'Contrôles', 'Traitement', 'Résiduel visé'], Object.entries(RES).map(([id, [p, g, tr, rp, rg]]) => [`**${id}**`, `${p} × ${g} = ${p * g} (${lvl(p * g)})`, CTRL[id], tr, `${rp} × ${rg} = ${rp * rg} (${lvl(rp * rg)})`]), [10, 22, 22, 24, 22]),
    SRC('Hypothèse des auteures : niveaux visés après mise en service des contrôles, à vérifier par le pilotage (C04, C06).'),
    P("Les contrôles préventifs réduisent surtout la **probabilité** (ils agissent sur les causes), tandis que la gravité de R03 reste élevée : un portefeuille dégradé coûte toujours cher. D'où l'importance des contrôles détectifs et correctifs, qui limitent les conséquences, comme le montre le « nœud papillon » de la figure 6.2."),
    ...FIGURE(1, '6.2', 'Nœud papillon du risque R03 : contrôles préventifs et détectifs'),
    H2('6.8 Limites de la mesure'),
    B("Les données proviennent des États-Unis (programme garanti par l'État) : ce sont des **repères**, à recalibrer sur l'historique de Crédit Horizon dès qu'il existera."),
    B("La LGD est rapportée au montant initial, faute d'encours au défaut publié ; elle ignore la part garantie par la SBA et les récupérations tardives."),
    B("Les facteurs relatifs sont multipliés comme s'ils étaient indépendants et le découpage en tranches de durée crée des effets de seuil (PD élevée des segments à 60 mois ou moins) ; une régression logistique corrigerait ces points."),
    B("Les parts en stades 2 et 3 et les niveaux résiduels sont des hypothèses ; en situation réelle, ils découleraient des retards observés et des tests de contrôle."),
    H3('Conclusion du chapitre 6'),
    P("La mesure prolonge la cartographie sans la remplacer : la cotation P × G hiérarchise les risques, la PD, la LGD et l'EAD chiffrent le coût du risque de crédit, et le stress test révèle la perte inattendue à absorber. Le contrôle interne reste la condition de cette mesure : sans pièces vérifiées, retards suivis et concentration revue, aucun paramètre n'est fiable. La conclusion générale revient sur la problématique à la lumière de cette mesure."),
  ];
} else if (which === 'G') {
  header = 'Annexe G – Ouverture facultative : mesure indicative du risque de crédit';
  body = [
    TITLE('Annexe G – Ouverture facultative : mesure indicative du risque de crédit'),
    P("Cette annexe facultative prolonge le dispositif qualitatif des chapitres 1 à 5. Elle adopte la posture de l'analyste risque crédit, propose une mesure indicative du risque de crédit (probabilité de défaut, perte en cas de défaut, pertes attendues, provisions et stress test) et approfondit plusieurs notions des cours de gestion des risques financiers et de contrôle interne : typologie et interdépendance des risques, risque inhérent et résiduel, stratégies de traitement."),
    P('Cette annexe est organisée en sections successives :'),
    ...['G.1 Statut de l\'annexe et rôle de l\'analyste risque crédit', 'G.2 Perte attendue, perte inattendue et provisions', 'G.3 Calibration sur des données publiques vérifiées', 'G.4 Application à un portefeuille fictif de 500 M MAD', 'G.5 Stress test et nature des risques', 'G.6 Typologie et interdépendance des risques', 'G.7 Risque inhérent, risque résiduel et traitement', 'G.8 Limites de la mesure'].map(SEC),
    H2("G.1 Statut de l'annexe et rôle de l'analyste risque crédit"),
    NOTE("**Annexe facultative, hors fiche.** La fiche projet demande une charte d'appétence qualitative, sans PD/LGD : les chapitres 1 à 5 respectent cette exigence et l'hypothèse H6 reste valable. Cette annexe n'est pas nécessaire aux livrables exigés ; elle propose un prolongement à titre d'illustration. Il n'utilise aucune donnée réelle de Crédit Horizon : les paramètres proviennent de données publiques externes (section G.3) et le portefeuille de 500 M MAD est fictif, construit pour la démonstration."),
    new Paragraph({ spacing: { after: 80 } }),
    P("La matrice RACI (section 4.4) confie à la fonction risques un avis indépendant sur l'octroi. Le profil de l'analyste risque crédit précise le contenu de cet avis : il s'agit de **mesurer** le risque, à l'échelle du dossier comme du portefeuille, et de proposer les moyens de le **maîtriser**."),
    CAP("Tableau G.1 – Profil de l'analyste risque crédit et traduction dans le dispositif"),
    T(['Critère', 'Analyste risque crédit', 'Traduction dans le dispositif'], [
      ['Mission principale', 'Évaluer, mesurer et maîtriser le risque de non-remboursement', 'Registre des risques (4.1), mesure du portefeuille (G.4)'], ['Orientation', 'Maîtrise du risque', "Charte d'appétence (5.1), plan d'action (5.5)"],
      ['Approche', 'Analyse individuelle et globale du portefeuille', 'Grille du dossier (5.3) ; portefeuille (G.4)'], ['Analyse financière', 'Oui, avec un focus sur le risque', 'Ratios du dossier, grille C01 (5.3)'],
      ['Garanties', 'Oui', 'Facteur garantie de la PD et de la LGD'], ['Probabilité de défaut (PD)', 'Oui : outil clé', 'PD calibrée (G.3)'],
      ['Suivi des impayés', 'Oui : suivi rapproché', 'Contrôle C05, risque R04'], ['Analyse du portefeuille', 'Approfondie : concentration, secteurs', 'HHI, trois premiers secteurs, contrôle C07'],
      ['Provisions et pertes attendues', 'Important : modélisation des pertes', 'Provisions IFRS 9 (G.2, G.4)'], ['Reporting', 'Important : indicateurs de risque', 'Indicateurs de pilotage (5.5), contrôle C08'],
      ['Compétences clés', 'Modèles PD, LGD, EAD ; Bâle II/III, IFRS 9', 'Sections G.2 à G.5'], ['Exemple concret', "Mesurer l'impact d'un défaut sur le portefeuille de 500 M et ajuster les provisions", 'Stress test (G.5)']].map(([a, b, c]) => [`**${a}**`, b, c]), [24, 40, 36]),
    SRC("Source : fiche de profil « Analyste risque crédit » ; colonne de droite : élaboration des auteures."),
    P("En résumé, l'analyste risque crédit se demande **« Quel est le risque ? », et comment le maîtriser**. Il éclaire la décision sans la prendre : l'autorisation reste du ressort de l'instance délégataire (contrôle C02)."),
    H2('G.2 Perte attendue, perte inattendue et provisions'),
    P("Le cours de gestion des risques (chapitre 1, section 8) distingue la **perte attendue**, estimation moyenne de la perte associée à une exposition, de la **perte inattendue**, qui dépasse ce niveau en cas de crise, de défauts simultanés ou d'événements extrêmes. Dans une représentation simplifiée du risque de crédit :"),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'EL = PD × LGD × EAD', bold: true, size: 26, color: PURPLE })], spacing: { before: 60, after: 120 } }),
    B("**PD** (probabilité de défaut) : probabilité qu'un emprunteur fasse défaut sur un horizon donné, ici 12 mois."),
    B("**LGD** (perte en cas de défaut) : part de l'exposition perdue après garanties et récupérations."),
    B("**EAD** (exposition au moment du défaut) : l'encours."),
    P("La perte attendue est un coût normal du métier, couvert par les **provisions** ; la perte inattendue doit être absorbée par les **fonds propres**. La norme IFRS 9 organise les provisions en trois stades : stade 1, pertes attendues à 12 mois ; stade 2 (dégradation significative), pertes attendues sur la durée de vie, avec une PD cumulée 1 − (1 − PD)^durée ; stade 3 (défaut), LGD × encours."),
    P("Conformément à l'hypothèse H2, le statut de Crédit Horizon n'est pas connu : Bâle II/III, les textes de Bank Al-Maghrib qui les transposent et IFRS 9 sont utilisés ici comme **bonnes pratiques de mesure**, non comme obligations."),
    ...FIGURE(3, 'G.1', 'De la probabilité de défaut aux provisions et aux fonds propres'),
    H2('G.3 Calibration sur des données publiques vérifiées'),
    P(`Faute de données propres (H6), les paramètres sont calibrés sur une source publique et vérifiable : les données « FOIA » du programme 7(a) de la **Small Business Administration** américaine (prêts garantis aux petites entreprises, cohortes ${ov.cohorts}, situation au 30/09/2026, licence U.S. Government Works). Le fichier brut de 545 751 lignes est téléchargé tel quel et son empreinte SHA-256 est enregistrée ; un pipeline Python applique neuf règles de nettoyage numérotées, conserve chaque ligne écartée avec sa règle et vérifie que lignes brutes = lignes retenues + lignes rejetées (544 605 + 1 146). Les données personnelles des emprunteurs sont supprimées.`),
    P("La préparation suit six étapes : **acquisition** (portail officiel, contrôle de la taille, empreinte et manifeste) ; **profilage** (chaque colonne lue en texte, sans conversion) ; **validation et nettoyage** (neuf règles numérotées et comptées, 1 136 doublons exacts et 10 prêts incohérents écartés) ; **minimisation** (nom, adresse et code postal supprimés) ; **agrégation** par cohorte, secteur, montant, durée et garantie ; **contrôle croisé** (taux de défaut recalculé indépendamment). Elle applique à la donnée deux objectifs du contrôle interne : un reporting fiable et la conformité."),
    P(`Sur ${n0(ov.loans_funded)} prêts décaissés, ${n0(ov.loans_resolved)} sont dénoués et ${n0(ov.defaults)} ont été passés en perte. La **PD annuelle** est un taux d'incidence : λ = défauts ÷ années d'exposition (${n0(ov.exposure_years)}), puis PD = 1 − e^(−λ) = **${pc(ov.pd_annual)}**. La **LGD** rapporte le montant passé en perte au montant initial des prêts concernés : **${pc(ov.lgd, 1)}**.`),
    CAP('Tableau G.2 – PD et LGD de référence selon la garantie et la durée'),
    T(['Segment', 'Prêts', 'Défaut sur la vie du prêt', 'PD 12 mois', 'LGD'], [
      ...[true, false].map((v) => { const r = pick('by_collateral', 'collateral', v); return [v ? 'Avec garantie réelle' : 'Sans garantie réelle', n0(r.loans), pc(r.default_rate), pc(r.pd_annual), pc(r.lgd, 1)]; }),
      ...['≤ 1 an', '1–5 ans', '5–10 ans', '> 10 ans'].map((v) => { const r = pick('by_term', 'term_band', v); return ['Durée ' + v, n0(r.loans), pc(r.default_rate), pc(r.pd_annual), pc(r.lgd, 1)]; }),
      ['**Ensemble**', n0(ov.loans_funded), pc(ov.default_rate), pc(ov.pd_annual), pc(ov.lgd, 1)]], [34, 14, 20, 16, 16], [1, 2, 3, 4]),
    SRC('Source : SBA, 7(a) FOIA FY2010–FY2019 ; calculs des auteures.'),
    P(`Ces repères rejoignent les constats qualitatifs du chapitre 4 : sans garantie réelle, la PD annuelle est supérieure de ${fr((pick('by_collateral', 'collateral', false).pd_annual / pick('by_collateral', 'collateral', true).pd_annual - 1) * 100, 0)} % (intérêt du contrôle C01) ; les crédits courts font défaut plus souvent ; la PD sectorielle va de ${pc(pick('by_sector', 'sector', 'Finance et assurance').pd_annual)} à ${pc(pick('by_sector', 'sector', 'Transport et entreposage').pd_annual)}.`),
    H2('G.4 Application à un portefeuille fictif de 500 M MAD'),
    P("Un portefeuille fictif de 500 M MAD est réparti en neuf segments sectoriels, avec pour chacun une part garantie, une durée moyenne et des parts d'encours en stades 2 et 3. La PD de chaque segment est la PD de référence multipliée par les facteurs relatifs du secteur, de la garantie et de la durée."),
    CAP('Tableau G.3 – Pertes attendues et provisions IFRS 9 du portefeuille fictif (en M MAD)'),
    T(['Secteur', 'EAD', 'Garanti', 'Durée', 'PD 12 mois', 'LGD', 'EL 12 mois', 'Stades 2/3', 'Provision'],
      [...el.rows.map((r) => [r.sector, mm(r.ead), r.collateral + ' %', r.term + ' m', pc(r.pd), pc(r.lgd, 0), mm(r.el12), `${r.stage2} / ${r.stage3} %`, mm(r.provision)]),
       ['**Total**', mm(el.ead), '', '', pc(wpd), pc(wlgd, 0), mm(el.el12), '', mm(el.provision)]], [27, 9, 8, 8, 10, 7, 10, 11, 10], [1, 2, 3, 4, 5, 6, 8]),
    SRC('Portefeuille fictif ; paramètres SBA ; calculs des auteures.'),
    P(`Les pertes attendues à 12 mois atteignent **${mm(el.el12)} MAD** et les provisions IFRS 9 **${mm(el.provision)} MAD** (${pc(el.coverage)} de l'encours). Environ 60 % des provisions proviennent des encours en stades 2 et 3, qui ne représentent que 11 % de l'encours : le suivi des retards (C05) conditionne directement le provisionnement. Les trois premiers secteurs pèsent ${pc(el.top3, 0)} de l'encours (indice de Herfindahl ${fr(el.hhi, 3)}), contre ${pc(ov.top3_sector_share, 0)} dans le portefeuille SBA : c'est le **risque de concentration** du cours, suivi par C07.`),
    H2('G.5 Stress test et nature des risques'),
    P("L'exemple type de l'analyste risque crédit consiste à « mesurer l'impact d'un défaut sur le portefeuille de 500 M et ajuster les provisions ». Quatre scénarios ont été simulés :"),
    CAP('Tableau G.4 – Résultats des scénarios de stress (en M MAD)'),
    T(['Scénario', 'Hypothèse', 'Nature du risque', 'Provisions', 'Couverture', 'Dotation supplémentaire'],
      [['Situation de base', '–', '–', mm(el.provision), pc(el.coverage), '–'],
       ...[['Récession modérée', 'PD × 1,5 ; LGD + 5 pts', 'Systématique'], ['Récession sévère', 'PD × 2 ; LGD + 10 pts', 'Systématique'], ['Crise du BTP', 'PD de la construction × 2,5', 'Sectoriel (concentration)'], ['Défaut 5 M MAD', "Défaut d'une contrepartie", 'Spécifique']].map(([k, h, n]) => { const s = sc[k]; return [k, h, n, mm(s.provision), pc(s.coverage), `+${mm(s.provision - el.provision)} (+${fr((s.provision / el.provision - 1) * 100, 0)} %)`]; })],
      [16, 24, 18, 12, 12, 18], [3, 4, 5]),
    SRC('Calculs des auteures.'),
    P(`En récession sévère, les provisions passent de ${mm(el.provision)} à ${mm(sc['Récession sévère'].provision)} MAD : l'écart de ${mm(sc['Récession sévère'].provision - el.provision)} MAD illustre une **perte inattendue**. Une récession est un **risque systématique** : la diversification ne la supprime pas, on la mesure par le stress test. Le défaut d'une seule contrepartie de 5 M MAD est un **risque spécifique**, réductible par la diversification ; il coûte toutefois ${mm(sc['Défaut 5 M MAD'].singleLoss)} MAD, soit ${fr(sc['Défaut 5 M MAD'].singleLoss / el.provision * 100, 0)} % des provisions de base, ce qui plaide pour une limite par contrepartie dans la charte (article 8).`),
    H2('G.6 Typologie et interdépendance des risques'),
    P("Le cours de gestion des risques (chapitre 2) distingue risques de marché (actions, taux, change, matières premières), de crédit (défaut, dégradation, contrepartie, concentration), de liquidité (de marché et de financement) et opérationnel (personnes, processus, systèmes, événements externes). Le tableau G.5 les rapporte à Crédit Horizon."),
    CAP('Tableau G.5 – Typologie du cours appliquée à Crédit Horizon'),
    T(['Risque', 'Exposition de Crédit Horizon', 'Niveau', 'Dans le dossier'], C.TYPOLOGY.map((x) => [`**${x.type}**`, x.exposure, x.level, x.where]), [24, 36, 12, 28]),
    SRC('Source : élaboration des auteures à partir du cours de gestion des risques financiers, chapitre 2.'),
    P("Les risques ne sont pas indépendants. Le cours illustre une chaîne taux → marché → crédit → liquidité. Chez Crédit Horizon, l'effet domino part de l'octroi : " + C.CHAIN.map((c) => `${c.id} (${c.text.toLowerCase()})`).join(' → ') + ". Un risque opérationnel et de crédit à l'entrée finit en risque de liquidité, ce qui justifie de traiter R01 et R02 en priorité."),
    H2('G.7 Risque inhérent, risque résiduel et traitement'),
    P("Les cotes P × G du chapitre 4 sont des cotes de **risque inhérent**, avant tout dispositif de maîtrise. Le cours définit le **risque résiduel** comme ce qui subsiste après la mise en place des dispositifs, et quatre stratégies de traitement : éviter, réduire, transférer, accepter. Le tableau G.6 propose, à titre d'hypothèse, le risque résiduel visé une fois les contrôles du chapitre 5 en service."),
    CAP('Tableau G.6 – Risque inhérent, traitement et risque résiduel visé'),
    T(['Risque', 'Inhérent (P × G)', 'Contrôles', 'Traitement', 'Résiduel visé'], Object.entries(RES).map(([id, [p, g, tr, rp, rg]]) => [`**${id}**`, `${p} × ${g} = ${p * g} (${lvl(p * g)})`, CTRL[id], tr, `${rp} × ${rg} = ${rp * rg} (${lvl(rp * rg)})`]), [10, 22, 22, 24, 22]),
    SRC('Hypothèse des auteures : niveaux visés après mise en service des contrôles, à vérifier par le pilotage (C04, C06).'),
    P("Les contrôles préventifs réduisent surtout la **probabilité** (ils agissent sur les causes), tandis que la gravité de R03 reste élevée : un portefeuille dégradé coûte toujours cher. D'où l'importance des contrôles détectifs et correctifs, qui limitent les conséquences, comme le montre le « nœud papillon » de la figure G.2."),
    ...FIGURE(1, 'G.2', 'Nœud papillon du risque R03 : contrôles préventifs et détectifs'),
    H2('G.8 Limites de la mesure'),
    B("Les données proviennent des États-Unis (programme garanti par l'État) : ce sont des **repères**, à recalibrer sur l'historique de Crédit Horizon dès qu'il existera."),
    B("La LGD est rapportée au montant initial, faute d'encours au défaut publié ; elle ignore la part garantie par la SBA et les récupérations tardives."),
    B("Les facteurs relatifs sont multipliés comme s'ils étaient indépendants et le découpage en tranches de durée crée des effets de seuil (PD élevée des segments à 60 mois ou moins) ; une régression logistique corrigerait ces points."),
    B("Les parts en stades 2 et 3 et les niveaux résiduels sont des hypothèses ; en situation réelle, ils découleraient des retards observés et des tests de contrôle."),
    H3("Conclusion de l'annexe G"),
    P("La mesure prolonge la cartographie sans la remplacer : la cotation P × G hiérarchise les risques, la PD, la LGD et l'EAD chiffrent le coût du risque de crédit, et le stress test révèle la perte inattendue à absorber. Le contrôle interne reste la condition de cette mesure : sans pièces vérifiées, retards suivis et concentration revue, aucun paramètre n'est fiable. Elle reste une illustration facultative : le cœur du dossier demeure le dispositif qualitatif des chapitres 4 et 5."),
  ];
} else if (which === 'F') {
  header = 'Annexe F – Correspondance avec les cours';
  const GR = 'Gestion des risques', CI = 'Contrôle interne';
  const rows = [
    ['Risque (effet de l\'incertitude sur les objectifs)', GR + ', ch. 1', 'Objectif de croissance prudente ; incertitude sur la capacité des TPE à rembourser', '2.1, 4.1'],
    ['Risque et perte', GR + ', ch. 1', 'Le registre recense des risques avant toute perte ; le registre des anomalies (C04) trace les incidents', '4.1, 5.2'],
    ['Incertitude et exposition', GR + ', ch. 1', 'Facteur : santé des TPE ; exposition : l\'encours ; événement : le défaut ; conséquence : la perte', 'G.3, G.4'],
    ['Cause, événement, conséquence', GR + ', ch. 1', 'Chaque risque est décrit par ses causes, l\'événement redouté et ses conséquences', '3.4, 4.1, annexe A'],
    ['Probabilité et impact', GR + ', ch. 1', 'Échelles semi-quantitatives de 1 à 5 ; PD quantitative en ouverture', '3.4, G.3'],
    ['Criticité = P × I', GR + ', ch. 1', 'R03 = 4 × 5 = 20 et R07 = 4 × 4 = 16 en zone critique', '3.4, 4.2'],
    ['Risque pur et risque spéculatif', GR + ', ch. 1', 'Octroyer un crédit est spéculatif (marge ou perte) ; le contournement du circuit (R07) est un risque pur', '4.1, G.1'],
    ['Perte attendue et perte inattendue', GR + ', ch. 1', 'EL = PD × LGD × EAD couverte par les provisions ; l\'écart en récession sévère relève des fonds propres', 'G.2, G.5'],
    ['Couple risque-rendement', GR + ', ch. 1', 'La croissance des volumes (rendement) contre la qualité du portefeuille (risque) : la problématique', 'Introduction, 5.1'],
    ['Diversification et concentration', GR + ', ch. 1', 'Suivi de la concentration (C07) ; trois premiers secteurs et indice de Herfindahl', '5.2, G.4'],
    ['Processus de gestion des risques', GR + ', ch. 1', 'Identifier, analyser, évaluer, hiérarchiser (ch. 4), traiter (ch. 5), surveiller (5.5)', 'Chapitres 3 à 5'],
    ['Catégories de risques', GR + ', ch. 1', 'Crédit (R01 à R04), liquidité (R05, R06), opérationnel (R07, R08)', '4.1, G.6'],
    ['Risque de marché', GR + ', ch. 2', 'Pas de portefeuille de titres : exposition directe faible', 'G.6'],
    ['Risque de taux', GR + ', ch. 2', 'Coût du refinancement et fragilité des TPE à taux variable', 'G.6'],
    ['Risque de change', GR + ', ch. 2', 'Exposition indirecte par les TPE clientes importatrices', 'G.6'],
    ['Risque de crédit : défaut, dégradation, contrepartie, concentration', GR + ', ch. 2', 'R03 et PD ; stade 2 d\'IFRS 9 ; contrepartie faible ; C07', '4.1, G.4, G.6'],
    ['Liquidité de marché et de financement', GR + ', ch. 2', 'R05 (décaissements accélérés) et R06 (échéances des ressources) ; C05', '4.1, G.6'],
    ['Risque opérationnel (personnes, processus, systèmes, externes)', GR + ', ch. 2', 'R07 (personnes, processus) et R08 (processus, données)', '4.1, G.6'],
    ['Risque spécifique et systématique', GR + ', ch. 2', 'Défaut d\'un client de 5 M MAD (spécifique) ; récession (systématique)', 'G.5'],
    ['Interdépendance des risques', GR + ', ch. 2', 'R02 → R01 → R03 → R04 → R05 → R06', '4.2.4, G.6'],
    ['Cartographie des risques', GR + ', ch. 2', 'Matrice P × G de 25 cases, classement et répartition', '4.2'],
    ['Risque inhérent et résiduel', GR + ', ch. 2', 'Cotes du registre = inhérent ; résiduel visé après les contrôles', 'G.7'],
    ['Stratégies de traitement', GR + ', ch. 2', 'Réduire par les contrôles ; transférer par les garanties et la diversification des ressources', '5.4, G.7'],
    ['Objectifs → risques → contrôles → assurance raisonnable', CI + ', ch. 1', 'La matrice de traçabilité relie chaque fait du cas à un risque, un contrôle et un indicateur', '5.6'],
    ['Approche traditionnelle et contemporaine', CI + ', ch. 1', 'Contrôles intégrés au circuit d\'octroi, avant la décision, plutôt qu\'a posteriori', '5.2, 5.3'],
    ['Définition et assurance raisonnable', CI + ', ch. 1', 'Même avec huit contrôles, un défaut reste possible : d\'où le suivi et les provisions', '2.2, G.2'],
    ['Définition du COSO', CI + ', ch. 1', 'Diagnostic des cinq composantes et des 17 principes', '2.2, 4.5, annexe C'],
    ['Préventif, détectif, correctif', CI + ', ch. 1', 'C01 à C03 préventifs ; C05, C07, C08 détectifs ; C04 et C06 détectifs et correctifs', '5.2'],
    ['Objectifs : opérations, reporting, conformité, actifs', CI + ', ch. 1', 'Qualité de l\'octroi (C01, C02), reporting (C08), délégations (C03), protection des créances (C05, C07)', '5.2'],
    ['Contrôle interne, audit interne, contrôle de gestion, gestion des risques', CI + ', ch. 1', 'Double validation (contrôle interne), revue indépendante (audit), volumes contre budget (contrôle de gestion), registre (risques)', '2.3, 4.3'],
    ['Gouvernance et rapport coût-bénéfice', CI + ', ch. 1', 'Huit contrôles ciblés, chacun relié à un risque et à un indicateur', '5.2, 5.5'],
    ['Les cinq composantes du COSO', CI + ', ch. 2', 'Maturité appréciée par composante et faiblesses associées', '2.2, 4.5'],
    ['Environnement de contrôle et tone at the top', CI + ', ch. 2', 'Décisions hors délégation (R07) : la charte et les délégations y répondent', '4.5, 5.1'],
    ['Évaluation des risques', CI + ', ch. 2', 'Registre P × G et cartographie', '3.4, 4.2'],
    ['Activités de contrôle et séparation des fonctions', CI + ', ch. 2', 'Constitution, analyse et autorisation séparées (C03) ; vérification par la matrice RACI', '4.4, 5.2'],
    ['Information et communication', CI + ', ch. 2', 'Remontée des anomalies (C04), contrôle du reporting (C08), circulation entre fonctions', '4.3.7, 5.2'],
    ['Activités de pilotage', CI + ', ch. 2', 'Indicateurs de pilotage et évaluation de l\'efficacité des contrôles (action A10)', '5.5, annexe C'],
    ['Organes responsables', CI + ', ch. 2', 'Fonctions commerciale, finance, risques, direction générale, contrôle interne', '4.3, 4.4'],
    ['Modèle des Trois Lignes', CI + ', ch. 2', 'Commercial (1re), fonction risques (2e), audit interne (3e), direction générale (gouvernance)', '2.3, 4.4'],
  ];
  body = [
    TITLE('Annexe F – Correspondance entre les cours et le rapport'),
    P("Le tableau F.1 situe chacune des notions des polycopiés de Gestion des risques financiers (chapitres 1 et 2) et de Contrôle interne (chapitres 1 et 2) du module « Contrôle et gestion des risques financiers » (Pr Z. ELMENZHI), indique son application au cas Crédit Horizon et renvoie aux sections du rapport où elle est mobilisée. Il complète l'articulation des deux enseignements présentée en section 5.6 ; les renvois G.x désignent l'annexe facultative G."),
    CAP('Tableau F.1 – Notions des cours, application au cas et sections du rapport'),
    T(['Notion', 'Cours', 'Application à Crédit Horizon', 'Sections'], rows.map(([a, b, c, d]) => [`**${a}**`, b, c, d]), [28, 16, 40, 16]),
    SRC('Source : élaboration des auteures à partir des deux polycopiés du module.'),
  ];
} else {
  header = 'Chapitre 7 – La plateforme Crédit Horizon Risk Intelligence';
  body = [
    TITLE('Chapitre 7 : La plateforme Crédit Horizon Risk Intelligence'),
    P("Ce chapitre présente la plateforme réalisée pour rendre le dispositif opérationnel : elle reprend les livrables des chapitres 4 à 6 (registre, cartographie, contrôles, charte, RACI, plan d'action, mesure du risque de crédit) dans un outil partagé, et ajoute un module de révision qui relie le projet aux deux cours."),
    P('Ce chapitre est organisé en sections successives :'),
    ...['7.1 Objectifs et principes', '7.2 Architecture fonctionnelle', "7.3 Parcours d'un dossier et séparation des fonctions", '7.4 Données de référence : de la donnée brute au tableau de bord', '7.5 Rôles, droits et traçabilité', '7.6 Module de révision et logique du contrôle interne', '7.7 Limites de la plateforme'].map(SEC),
    H2('7.1 Objectifs et principes'),
    B("**Aide à la décision, jamais décision automatique** : aucune fonction n'accorde ni ne refuse un crédit ; l'autorisation reste à l'instance délégataire (C02)."),
    B("**Traçabilité** : chaque création, modification ou suppression est journalisée (qui, quand, quoi), ce qui sert le pilotage (COSO, principes 16 et 17)."),
    B("**Transparence des données** : les données de démonstration sont signalées comme telles ; les repères externes indiquent leur source et leur date."),
    B("**Un seul référentiel** : un même registre alimente la cartographie, les contrôles, les recommandations, le plan d'action et les indicateurs, comme la matrice de traçabilité du tableau 5.17."),
    H2('7.2 Architecture fonctionnelle'),
    CAP('Tableau 7.1 – Modules de la plateforme et livrables correspondants'),
    T(['Module', 'Contenu', 'Livrable du rapport'], [
      ['Dashboard exécutif', 'Indicateurs clés, répartition et évolution des risques, top 5, cartographie, provisions par secteur', 'Sections 4.2, 5.5'],
      ['Registre des risques', 'Fiches R01 à R08 : cause, événement, conséquence, P × G, inhérent et résiduel, traitement', 'Section 4.1, annexe A, tableau 6.6'],
      ['Risque de crédit', 'PD, LGD, EAD, pertes attendues, provisions IFRS 9, stress test, fiche de l\'analyste', 'Chapitre 6'],
      ['Dossiers TPE', 'Saisie, grille de pièces C01, blocage si incomplet, mesure indicative du risque', 'Section 5.3'],
      ['Contrôles et COSO', 'Fiches C01 à C08, diagnostic des 17 principes et maturité par composante', 'Sections 4.5, 5.2, annexes B et C'],
      ['Appétence et gouvernance', "Charte, matrice RACI, délégations, Trois Lignes, typologie des risques", 'Sections 4.4, 5.1, 6.6'],
      ['Suivi et plan d\'action', 'Recommandations, actions A01 à A10, registre des anomalies', 'Sections 5.4, 5.5'],
      ['Portefeuille de référence', 'Repères de défaut SBA, source et méthode de préparation', 'Section 6.3'],
      ['Risk Advisor IA', 'Assistant qui répond à partir des données de la plateforme, sans inventer', 'Chaînes de recommandations'],
      ['Cours et révision', 'Notions des deux cours appliquées au projet, carte mentale, schémas, quiz', 'Section 7.6'],
    ].map(([a, b, c]) => [`**${a}**`, b, c]), [22, 52, 26]),
    SRC('Source : plateforme Crédit Horizon Risk Intelligence (application web).'),
    ...FIGURE(0, '7.1', 'Carte mentale du projet et de la plateforme'),
    H2("7.3 Parcours d'un dossier et séparation des fonctions"),
    P("La plateforme applique le circuit d'octroi du chapitre 5. Un dossier incomplet est bloqué avant l'avis (C01) ; l'avis de la fonction risques s'appuie sur la grille commune et sur une mesure indicative (PD, LGD, perte attendue) ; la décision revient à l'instance délégataire (C02) ; le suivi des retards et des anomalies renvoie à une réévaluation du risque."),
    ...FIGURE(2, '7.2', "Parcours d'un dossier TPE dans la plateforme"),
    P("Ce parcours applique la **séparation des fonctions** du cours de contrôle interne (chapitre 2) : autorisation (instance délégataire), exécution (chargé d'affaires, puis décaissement par la finance), enregistrement (fonction finance) et contrôle (fonction risques et audit) ne sont jamais dans les mêmes mains. Le tableau 7.2 situe les acteurs dans le modèle des Trois Lignes de l'IIA."),
    CAP('Tableau 7.2 – Le modèle des Trois Lignes appliqué à Crédit Horizon'),
    T(['Ligne', 'Rôle', 'Acteurs de Crédit Horizon', 'Contrôles et outils'], C.THREE_LINES.map((l) => [`**${l.line}**`, l.role, l.ch, l.controls]), [17, 27, 30, 26]),
    SRC("Source : élaboration des auteures à partir du modèle des Trois Lignes (IIA, 2020) et de la matrice RACI (tableau 4.5)."),
    H2('7.4 Données de référence : de la donnée brute au tableau de bord'),
    P("Les repères de défaut (section 6.3) sont produits par un pipeline reproductible, documenté pour pouvoir être refait à partir de zéro :"),
    B("**Acquisition** : téléchargement depuis le portail officiel data.sba.gov, contrôle de la taille, calcul de l'empreinte SHA-256 et manifeste."),
    B("**Profilage** : chaque colonne est lue en texte, sans conversion : valeurs vides, valeurs distinctes, formats, écarts avec le dictionnaire officiel."),
    B("**Validation et nettoyage** : neuf règles numérotées (espaces, doublons, codes, montants, dates, cohérence garantie / montant, cohérence statut / dates, données personnelles, variables dérivées). 1 136 doublons exacts et 10 prêts sans date de passage en perte sont écartés et conservés dans un journal des rejets."),
    B("**Minimisation** : nom, adresse et code postal des emprunteurs sont supprimés, car inutiles à l'analyse du risque."),
    B("**Tables d'analyse** : agrégats par cohorte, secteur, montant, durée, ancienneté, garantie, avec des définitions uniques (taux de défaut, PD annuelle, LGD)."),
    B("**Contrôle croisé** : le taux de défaut est recalculé indépendamment à partir du fichier brut, et sept tests automatisés vérifient le pipeline."),
    P("Cette démarche applique à la donnée les objectifs du contrôle interne : un **reporting fiable** (réconciliation 545 751 = 544 605 + 1 146) et la **conformité** (protection des données personnelles)."),
    H2('7.5 Rôles, droits et traçabilité'),
    P("Les droits de la plateforme reprennent la matrice RACI : administrateur, direction générale, analyste risque crédit, chargé d'affaires, contrôle interne et lecteur. Le chargé d'affaires peut saisir un dossier mais pas modifier le registre ni donner d'avis ; le contrôle interne consulte et déclare des anomalies ; un nouveau membre est en lecture seule tant qu'un rôle ne lui est pas attribué. Ces restrictions sont des **contrôles informatiques**, une catégorie d'activités de contrôle du COSO."),
    H2('7.6 Module de révision et logique du contrôle interne'),
    P("Le module « Cours et révision » relie 39 notions des deux cours (Pr Z. ELMENZHI) à leur application dans le projet : pour chacune, une définition, une phrase à retenir et l'exemple tiré de Crédit Horizon. Il contient aussi la carte mentale (figure 7.1), les schémas des figures 6.1, 6.2 et 7.2, les 30 questions d'auto-évaluation des polycopiés et leurs 12 exercices corrigés. La figure 7.3 résume la logique qui organise l'ensemble."),
    ...FIGURE(4, '7.3', 'La boucle du contrôle interne appliquée au projet'),
    H2('7.7 Limites de la plateforme'),
    B("Les anomalies, dossiers, avancements et le portefeuille de 500 M MAD sont des **données de démonstration** ; ils doivent être remplacés par les données réelles de l'organisme."),
    B("L'assistant IA formule des propositions à partir des données saisies ; il ne remplace ni l'analyse de la fonction risques ni la décision de l'instance délégataire."),
    B("La plateforme est un prototype académique : un déploiement réel exigerait une revue de sécurité, une politique de sauvegarde et une validation par l'audit interne."),
    H3('Conclusion du chapitre 7'),
    P("La plateforme transforme le dossier en outil de travail : le registre, la charte, les contrôles et le plan d'action ne sont plus des documents figés mais un dispositif partagé, tracé et suivi. Elle applique elle-même les principes qu'elle sert : séparation des fonctions, traçabilité, fiabilité des données et aide à la décision sans automatisme."),
  ];
}
const doc = new Document({
  styles: { default: { document: { run: { font: F, size: 23 } } } },
  numbering: { config: [
    { reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 240 } }, run: { color: PURPLE } } }] },
    { reference: 's', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 240 } }, run: { color: PURPLE } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1430, bottom: 1520, left: 1418, right: 1418, header: 620, footer: 700 }, pageNumbers: { start } } },
    headers: { default: new Header({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: W }], border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF', space: 4 } }, children: [new TextRun({ text: header, italics: true, size: 18, color: PURPLE }), new TextRun({ text: '\t' }), new ImageRun({ type: 'png', data: fs.readFileSync(R + '/logo.png'), transformation: { width: 92, height: 25 } })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 23, color: INK })] })] }) },
    children: body }],
});
Packer.toBuffer(doc).then((b) => fs.writeFileSync(out, b));
