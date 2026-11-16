const fs = require('fs');
const D = JSON.parse(fs.readFileSync('/home/user/fatima-portfolio/credit-horizon-site/src/seed.json'));
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType, HeadingLevel, LevelFormat, BorderStyle, Footer, PageNumber } = require('docx');
const F = 'Calibri', W = 9638;
const runs = (t, o = {}) => String(t).split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) => s.startsWith('**') ? new TextRun({ text: s.slice(2, -2), bold: true, ...o }) : new TextRun({ text: s, ...o }));
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 100, line: 276 }, ...o });
const H1 = (t, br = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: br, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = (t) => new Paragraph({ children: runs(t), numbering: { reference: 'b', level: 0 }, spacing: { after: 50, line: 264 } });
const bd = { style: BorderStyle.SINGLE, size: 4, color: 'C8C2DA' };
function T(head, rows, widths) {
  const tot = widths.reduce((a, b) => a + b, 0); widths = widths.map((w) => Math.round(w * W / tot)); widths[widths.length - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, h) => new TableCell({ width: { size: widths[i], type: WidthType.DXA }, borders: { top: bd, bottom: bd, left: bd, right: bd }, shading: h ? { type: ShadingType.CLEAR, fill: '57369A', color: 'auto' } : undefined, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: runs(String(t), h ? { size: 18, bold: true, color: 'FFFFFF' } : { size: 18 }) })] });
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }), ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false)) }))] });
}
const lvl = (s) => (s >= 16 ? 'Critique' : s >= 10 ? 'Élevé' : s >= 5 ? 'Modéré' : 'Faible');
const QA = [
  ["Quelle est votre problématique ?", "Comment réconcilier les objectifs de croissance et de prudence de Crédit Horizon en structurant l'appétence au risque et les contrôles internes ?"],
  ["Pourquoi une démarche qualitative ?", "La fiche l'exige (charte sans PD/LGD) et le cas ne fournit aucune donnée chiffrée (hypothèse H6). Les cotes P et G sont des jugements argumentés, chacun justifié par un fait du cas ou une hypothèse signalée."],
  ["Pourquoi R03 est-il le risque le plus critique ?", "P = 4 car la tension volume / qualité est un fait du cas et les incitations poussent au volume ; G = 5 car il menace la viabilité de la stratégie et, par cascade, la liquidité. Criticité 20."],
  ["Pourquoi R04 n'est-il que modéré ?", "Le cas établit un suivi des anomalies insuffisant, mais ne dit pas que des retards ont déjà été détectés tardivement : P = 3 (hypothèse). G = 3 car l'impact croît avec la durée du retard."],
  ["Quelle différence entre cause, événement et conséquence ?", "La cause provoque (pièces manquantes), l'événement se produit (crédit accordé sur dossier incomplet), la conséquence est l'impact (perte, garantie inutilisable). Exemple R01."],
  ["Expliquez la matrice RACI.", "14 activités du processus d'octroi et de suivi ; une seule responsabilité finale (A) par activité ; aucun acteur ne cumule constitution, analyse et autorisation. C'est la séparation des fonctions."],
  ["Quelles sont les cinq composantes du COSO ?", "Environnement de contrôle, évaluation des risques, activités de contrôle, information et communication, pilotage. Chez Crédit Horizon, les faiblesses majeures portent sur l'environnement de contrôle (délégations imprécises) et les activités de contrôle (pas de contrôle de complétude indépendant ni de double validation)."],
  ["Différence entre contrôle préventif et détectif ?", "Préventif : avant l'événement (C01 complétude, C02 double validation, C03 séparation). Détectif : repère après (C05 retards, C07 concentration). C04 et C06 sont aussi correctifs."],
  ["Les textes de Bank Al-Maghrib s'appliquent-ils ?", "Pas forcément : le statut juridique de Crédit Horizon n'est pas connu (H2). Nous les traitons comme références conditionnelles ; certains n'ont été vérifiés que par leur intitulé et leur date."],
  ["Que contient la charte d'appétence ?", "13 articles qualitatifs et trois niveaux : risques acceptables sous contrôle, risques nécessitant une autorisation renforcée, risques inacceptables (par exemple un dossier incomplet décaissé)."],
  ["Comment avez-vous articulé les deux cours ?", "Les défauts de gouvernance de l'octroi (contrôle interne) sont reliés aux risques de crédit et aux conflits d'objectifs (gestion des risques) par le tableau d'articulation et la matrice de traçabilité (5.6) ; l'annexe F situe chaque notion des cours."],
  ["Pourquoi R04 et R06 posent-ils un problème de couverture ?", "Ils ne reposent que sur C05 : ce contrôle devient un point de dépendance à surveiller en priorité."],
  ["Votre dispositif garantit-il qu'il n'y aura plus de défaut ?", "Non : le contrôle interne ne donne qu'une assurance raisonnable. Le risque résiduel subsiste, d'où le suivi par les indicateurs et le plan d'action."],
  ["Pourquoi l'annexe G ?", "C'est une ouverture facultative, hors fiche : une illustration de la mesure du risque de crédit (PD, LGD, pertes attendues) sur des données publiques et un portefeuille fictif. Elle ne modifie pas les livrables, qui restent qualitatifs."],
  ["Quelle est la première action à lancer ?", "Les actions P1 : formaliser les délégations (A01), la checklist des pièces (A02), la double validation (A03) et le registre des anomalies (A04)."],
];
const children = [
  new Paragraph({ children: [new TextRun({ text: 'Crédit Horizon', bold: true, size: 52, color: '24233A' })], spacing: { after: 60 } }),
  new Paragraph({ children: [new TextRun({ text: 'Guide de préparation de la soutenance', size: 32, color: '57369A' })], spacing: { after: 200 } }),
  P("La soutenance est **individuelle** (2 points) : chacune doit pouvoir expliquer les huit risques, les cotations, les cinq composantes COSO, le RACI et les recommandations, quelle que soit la partie présentée."),
  H2('Proposition de plan (10 à 12 minutes, à adapter)'),
  T(['Temps', 'Contenu', 'Support dans le rapport'], [
    ['1 min', 'Le cas, les 5 dysfonctionnements, la problématique', 'Introduction, 1.3, 1.4'],
    ['1 min', 'La démarche qualitative, hypothèses H2 et H6', '1.7, chapitre 3'],
    ['3 min', 'Les 8 risques, la cotation P × G, la cartographie', '4.1, 4.2, figure 4.1'],
    ['2 min', 'Les acteurs, les conflits d\'objectifs, le RACI', '4.3, 4.4'],
    ['1 min', 'Le diagnostic COSO', '4.5'],
    ['3 min', 'Charte, contrôles, recommandations, plan d\'action', 'Chapitre 5'],
    ['1 min', 'Conclusion : réponse à la problématique, limites', 'Conclusion générale']], [12, 58, 30]),
  P(''),
  P("**Phrase de réponse à retenir :** le conflit entre croissance et prudence n'est pas une fatalité ; il devient dangereux lorsqu'aucune règle ne l'arbitre. Une charte d'appétence, une séparation effective des fonctions et quelques contrôles ciblés maintiennent la croissance dans des limites explicites."),

  H1('1. Le cas en 5 dysfonctionnements'),
  T(['Code', 'Dysfonctionnement'], D.dysfunctions.map((x) => [x.id, x.text]), [12, 88]),
  P(''),
  P("**Hypothèses clés :** H2, le statut juridique est inconnu, donc aucun texte marocain n'est présumé applicable ; H6, aucune donnée chiffrée, donc des cotations qualitatives."),
  H2('Échelles et seuils'),
  P("Probabilité et gravité de 1 à 5. Criticité = P × G : **1–4 faible, 5–9 modéré, 10–15 élevé, 16–25 critique**."),

  H1('2. Les huit risques'),
  T(['Risque', 'P × G', 'Niveau', 'Contrôles', 'Responsable'], D.risks.map((r) => [`**${r.id}** ${r.title}`, `${r.probability} × ${r.gravity} = ${r.probability * r.gravity}`, lvl(r.probability * r.gravity), r.control_ids, r.owner]), [36, 12, 10, 14, 28]),
  P(''),
  H2('Justifications des cotes (à savoir expliquer)'),
  ...D.risks.map((r) => B(`**${r.id}** : ${r.justification}`)),

  H1('3. Contrôle interne'),
  H2('Les cinq composantes COSO chez Crédit Horizon'),
  T(['Composante', 'Faiblesse', 'Recommandation'], D.coso_components.map((c) => [`**${c.name}** (${c.principles})`, c.gaps, c.recommendations]), [22, 39, 39]),
  P(''),
  H2('Les huit contrôles'),
  T(['Contrôle', 'Nature', 'Risques'], D.controls.map((c) => [`**${c.id}** ${c.name}`, c.nature, c.risk_ids]), [58, 22, 20]),
  P(''),
  H2('RACI : les trois idées'),
  B("14 activités, de la réception de la demande à la révision des procédures."),
  B("Une seule responsabilité finale (A) par activité."),
  B("Aucun acteur ne cumule constitution (commercial), analyse (fonction risques) et autorisation (direction générale ou comité de crédit)."),
  H2("Charte d'appétence : trois niveaux"),
  ...D.appetite_levels.map((l) => B(`**${l.title}** : ${l.description}`)),

  H1('4. Les huit recommandations'),
  P("Format : RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI."),
  T(['Risque', 'Lacune COSO', 'Action', 'Responsable', 'Indicateur'], D.recommendations.map((r) => [`**${r.risk_id}**`, r.coso_gap, r.action, r.owner, r.indicator]), [8, 24, 30, 20, 18]),

  H1('5. Questions probables du jury'),
  ...QA.flatMap(([q, a], i) => [new Paragraph({ children: [new TextRun({ text: `${i + 1}. ${q}`, bold: true })], spacing: { before: 140, after: 40 }, keepNext: true }), P(a, { indent: { left: 300 } })]),
  H2('Pièges à éviter'),
  B("Présenter les cotes comme des mesures : ce sont des jugements argumentés."),
  B("Dire que les textes de Bank Al-Maghrib ou de l'AMMC s'appliquent : cela dépend du statut (H2)."),
  B("Présenter l'annexe G comme un livrable : elle est facultative et hors fiche."),
  B("Confondre contrôle interne (fait fonctionner les contrôles) et audit interne (les évalue en toute indépendance)."),
  B("Promettre une absence de défaut : le contrôle interne ne donne qu'une assurance raisonnable."),
];
const doc = new Document({
  creator: 'F. Z. Chakib, I. Mouichou', title: 'Crédit Horizon – Guide de soutenance',
  styles: { default: { document: { run: { font: F, size: 22 } } }, paragraphStyles: [
    { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: F, size: 34, bold: true, color: '24233A' }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true, outlineLevel: 0 } },
    { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: F, size: 26, bold: true, color: '57369A' }, paragraph: { spacing: { before: 260, after: 120 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 500, hanging: 260 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: 'Crédit Horizon · Guide de soutenance   ', size: 16, color: '64748B' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '64748B' })] })] }) },
    children }],
});
Packer.toBuffer(doc).then((b) => fs.writeFileSync(process.argv[2], b));
