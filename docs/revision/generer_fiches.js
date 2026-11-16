const fs = require('fs');
const C = JSON.parse(fs.readFileSync(__dirname + '/course.json'));
const K = JSON.parse(fs.readFileSync(__dirname + '/calc.json'));
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType, HeadingLevel, LevelFormat, BorderStyle, Footer, PageNumber, PageBreak, ImageRun } = require('docx');
const F = 'Calibri', W = 9638;
const fr = (v, d = 2) => v.toFixed(d).replace('.', ',');
const runs = (t, o = {}) => t.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) => s.startsWith('**') ? new TextRun({ text: s.slice(2, -2), bold: true, ...o }) : new TextRun({ text: s, ...o }));
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 100, line: 276 }, ...o });
const H1 = (t, br = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: br, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = (t) => new Paragraph({ children: runs(t), numbering: { reference: 'b', level: 0 }, spacing: { after: 50, line: 264 } });
const bd = { style: BorderStyle.SINGLE, size: 4, color: 'C9D3CF' }, nb = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const cellP = (t, o = {}) => new Paragraph({ children: runs(String(t), { size: 19, ...o }), spacing: { after: 30 } });
function T(head, rows, widths) {
  const tot = widths.reduce((a, b) => a + b, 0); widths = widths.map((w) => Math.round(w * W / tot)); widths[widths.length - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, h) => new TableCell({ width: { size: widths[i], type: WidthType.DXA }, borders: { top: bd, bottom: bd, left: bd, right: bd }, shading: h ? { type: ShadingType.CLEAR, fill: '0A4D38', color: 'auto' } : undefined, margins: { top: 50, bottom: 50, left: 90, right: 90 }, children: [cellP(t, h ? { bold: true, color: 'FFFFFF' } : {})] });
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }), ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false)) }))] });
}
// carte de notion : 3 lignes (définition, à retenir, projet)
function card(c) {
  const row = (label, text, fill, color) => new TableRow({ cantSplit: true, children: [
    new TableCell({ width: { size: 1900, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill, color: 'auto' }, borders: { top: nb, bottom: nb, left: nb, right: nb }, margins: { top: 60, bottom: 60, left: 110, right: 80 }, children: [cellP(label, { bold: true, color })] }),
    new TableCell({ width: { size: W - 1900, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill, color: 'auto' }, borders: { top: nb, bottom: nb, left: nb, right: nb }, margins: { top: 60, bottom: 60, left: 80, right: 110 }, children: [cellP(text, label === 'À retenir' ? { bold: true } : {})] })] });
  return [new Paragraph({ children: [new TextRun({ text: c.title, bold: true, size: 25, color: '0A4D38' })], spacing: { before: 200, after: 70 }, keepNext: true, keepLines: true }),
    new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [1900, W - 1900], rows: [row('Définition', c.def, 'F8FAFC', '475569'), row('À retenir', c.key, 'FEF3C7', '92400E'), row('Dans le projet', c.project, 'ECFDF5', '0F7A58')] })];
}
const FIGS = JSON.parse(fs.readFileSync(__dirname + '/docfig.json'));
const figBlock = (f, i) => [H2(f.title), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, children: [new ImageRun({ type: 'png', data: fs.readFileSync(__dirname + `/docfig-${i}.png`), transformation: { width: 640, height: Math.round(640 * f.h / f.w) } })] }),
  new Paragraph({ children: [new TextRun({ text: f.caption, italics: true, size: 19, color: '475569' })], spacing: { after: 160 } })];
const el = K.base, sev = K.scen['Récession sévère'];
const mm = (v) => fr(v / 1e6, 2) + ' M MAD';
const children = [
  new Paragraph({ children: [new TextRun({ text: 'Crédit Horizon', bold: true, size: 52, color: '0A4D38' })], spacing: { after: 60 } }),
  new Paragraph({ children: [new TextRun({ text: 'Fiches de révision : le projet et les deux cours', size: 32, color: '334155' })], spacing: { after: 200 } }),
  P('Module « Contrôle et gestion des risques financiers » · Pr Z. ELMENZHI · Génie financier, 5e année · EMSI Tanger'),
  P('Ce document relie chaque notion des cours de **gestion des risques financiers** (chapitres 1 et 2) et de **contrôle interne** (chapitres 1 et 2) à son application dans le projet Crédit Horizon. Pour chaque notion : une définition fidèle au cours, une phrase **à retenir**, et l\'exemple tiré du projet. Les mêmes contenus sont disponibles dans la plateforme, page « Cours et révision », avec un quiz interactif.'),
  H2('Méthode pour retenir'),
  B('**Lire** une fiche, puis la refermer et **réciter** la phrase « À retenir » et l\'exemple du projet.'),
  B('**Se tester** avec les 30 questions (partie 5) : répondre à voix haute avant de lire la réponse.'),
  B('**Relier** : pour chaque notion, se demander « où est-ce dans Crédit Horizon ? ». C\'est cet ancrage qui fait retenir.'),
  B('La veille : relire uniquement le **mémo** (partie 4).'),

  H1('1. Le projet en une page'),
  P('**Le problème.** Crédit Horizon, organisme fictif de financement des TPE, veut croître vite. Ses dossiers sont parfois incomplets, ses décisions d\'octroi hétérogènes et ses anomalies mal suivies : la croissance menace la prudence.'),
  P('**La question.** Comment concilier croissance et prudence grâce à la gestion des risques et au contrôle interne ?'),
  P('**La méthode.** Le cours de gestion des risques sert à identifier, coter et mesurer les risques. Le cours de contrôle interne sert à concevoir les contrôles (COSO 2013) et à répartir les responsabilités (RACI, Trois Lignes).'),
  P('**La réponse.** Une charte d\'appétence, 8 contrôles, des recommandations et un plan d\'action, et un suivi continu dans la plateforme.'),
  H2('Le fil rouge'),
  T(['Étape', 'Dans Crédit Horizon'], [
    ['1. Objectifs', 'Croître en volume tout en restant prudent'], ['2. Risques', '8 risques R01 à R08, cotés probabilité × gravité'], ['3. Mesure', 'PD, LGD, EAD → pertes attendues et provisions IFRS 9'],
    ['4. Contrôles', '8 contrôles C01 à C08 (préventifs et détectifs)'], ['5. Acteurs', 'Matrice RACI et modèle des Trois Lignes'], ['6. Surveillance', 'Registre des anomalies, indicateurs, dashboard'], ['7. Amélioration', 'Recommandations et plan d\'action']], [25, 75]),
  H2('Les chiffres à retenir'),
  T(['Élément', 'Valeur'], [
    ['Risques', '8 : 4 de crédit (R01–R04), 2 de liquidité (R05–R06), 2 opérationnels (R07–R08)'],
    ['Risques critiques', 'R03 Dégradation du portefeuille (4 × 5 = 20) et R07 Décision hors délégation (4 × 4 = 16)'],
    ['Contrôles', '8 : C01, C02, C03 préventifs ; C05, C07, C08 détectifs ; C04, C06 détectifs et correctifs'],
    ['COSO 2013', '5 composantes, 17 principes'],
    ['Pertes attendues à 12 mois', `${mm(el.el12)} (EL = PD × LGD × EAD, portefeuille fictif de 500 M MAD)`],
    ['Provisions IFRS 9', `${mm(el.provision)}, soit ${fr(el.coverage * 100)} % de l'encours ; ${mm(sev.provision)} en récession sévère`],
    ['Repères de défaut (SBA)', 'PD annuelle 1,35 % ; LGD 61 % ; calculés sur 478 641 prêts réels'],
  ], [32, 68]),
  H2('Les 8 risques du registre'),
  T(['Code', 'Risque', 'Catégorie', 'P × G', 'Traitement'], [
    ['R01', 'Octroi sur dossier incomplet ou incohérent', 'Crédit', '5 × 3 = 15', 'Réduire'], ['R02', 'Critères d\'octroi non harmonisés', 'Crédit', '4 × 3 = 12', 'Réduire'],
    ['R03', 'Dégradation du portefeuille sous pression des volumes', 'Crédit', '4 × 5 = 20', 'Réduire et transférer'], ['R04', 'Retards de remboursement détectés tardivement', 'Crédit', '3 × 3 = 9', 'Réduire'],
    ['R05', 'Tension de trésorerie (décaissements accélérés)', 'Liquidité', '3 × 4 = 12', 'Réduire'], ['R06', 'Inadéquation échéances des crédits / ressources', 'Liquidité', '2 × 5 = 10', 'Réduire et transférer'],
    ['R07', 'Décision hors délégation, contournement du circuit', 'Opérationnel', '4 × 4 = 16', 'Réduire'], ['R08', 'Anomalies non remontées, données de mauvaise qualité', 'Opérationnel', '4 × 3 = 12', 'Réduire']], [9, 45, 16, 14, 16]),

  H1('1 bis. Carte mentale et schémas'),
  P('Commencez par ces images : elles résument tout le projet. Les mêmes figures sont interactives dans la plateforme (Cours et révision, onglet « Carte mentale et schémas »).'),
  ...FIGS.flatMap(figBlock),
  H1('2. Gestion des risques financiers'),
  ...[1, 2].flatMap((ch) => [H2(`Chapitre ${ch} — ${ch === 1 ? 'Cadre conceptuel des risques financiers' : 'Typologie approfondie des risques financiers'}`), ...C.CONCEPTS.filter((c) => c.course === 'GR' && c.chap === ch).flatMap(card)]),
  H2('Typologie du cours appliquée à Crédit Horizon'),
  T(['Risque', 'Exposition de Crédit Horizon', 'Niveau', 'Dans le projet'], C.TYPOLOGY.map((x) => [x.type, x.exposure, x.level, x.where]), [24, 34, 12, 30]),
  P(''), P('**Effet domino chez Crédit Horizon :** ' + C.CHAIN.map((c) => `${c.id} (${c.text.toLowerCase()})`).join(' → ') + '.'),

  H1('3. Contrôle interne'),
  ...[1, 2].flatMap((ch) => [H2(`Chapitre ${ch} — ${ch === 1 ? 'Fondements, définition et objectifs du contrôle interne' : 'Composantes et organes responsables du contrôle interne'}`), ...C.CONCEPTS.filter((c) => c.course === 'CI' && c.chap === ch).flatMap(card)]),
  H2('Les Trois Lignes chez Crédit Horizon'),
  T(['Ligne', 'Rôle', 'Acteurs', 'Contrôles'], C.THREE_LINES.map((l) => [l.line, l.role, l.ch, l.controls]), [16, 26, 30, 28]),
  P(''),
  H2('Quatre fonctions à ne pas confondre'),
  T(['Fonction', 'Finalité', 'Exemple chez Crédit Horizon'], C.FUNCTIONS.map((f) => [f.name, f.goal, f.ch]), [24, 36, 40]),

  H1('4. Mémo : à relire la veille'),
  T(['Notion', 'Moyen mnémotechnique', 'Détail'], C.MEMO.map((m) => [m.label, `**${m.mnemo}**`, m.detail]), [30, 30, 40]),

  H1('5. Quiz : les 30 questions d\'auto-évaluation'),
  P('Cacher la réponse, répondre à voix haute, puis vérifier.'),
  ...['GR', 'CI'].flatMap((co) => [H2(co === 'GR' ? 'Gestion des risques financiers' : 'Contrôle interne'), ...C.QUIZ.filter((q) => q.course === co).flatMap((q, i) => [
    new Paragraph({ children: [new TextRun({ text: `${i + 1}. ${q.q}`, bold: true })], spacing: { before: 120, after: 40 }, keepNext: true }),
    new Paragraph({ children: [new TextRun({ text: 'Réponse : ', italics: true, color: '0F7A58' }), new TextRun({ text: q.a })], spacing: { after: 60 }, indent: { left: 360 } })])]),

  H1('6. Exercices des polycopiés, corrigés'),
  ...['GR', 'CI'].flatMap((co) => [H2(co === 'GR' ? 'Gestion des risques financiers (chapitre 2)' : 'Contrôle interne (chapitres 1 et 2)'), ...C.EXERCISES.filter((x) => x.course === co).flatMap((x) => [
    new Paragraph({ children: [new TextRun({ text: `${x.title}${co === 'CI' ? ` (chapitre ${x.chap})` : ''}`, bold: true, size: 24, color: '0A4D38' })], spacing: { before: 180, after: 60 }, keepNext: true }),
    new Paragraph({ children: [new TextRun({ text: x.statement, italics: true, color: '475569' })], spacing: { after: 60 }, keepNext: true }),
    ...x.solution.map(B)])]),
];
const doc = new Document({
  creator: 'F. Z. Chakib, I. Mouichou', title: 'Crédit Horizon – Fiches de révision',
  styles: { default: { document: { run: { font: F, size: 22 } } }, paragraphStyles: [
    { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: F, size: 36, bold: true, color: '0A4D38' }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true, outlineLevel: 0 } },
    { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: F, size: 27, bold: true, color: '0F7A58' }, paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 500, hanging: 260 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: 'Crédit Horizon · Fiches de révision   ', size: 16, color: '64748B' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '64748B' })] })] }) },
    children }],
});
Packer.toBuffer(doc).then((b) => fs.writeFileSync(process.argv[2], b));
