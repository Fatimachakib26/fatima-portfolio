import pymupdf, re, json
FD='/usr/share/fonts/truetype/liberation/'
REG=pymupdf.Font(fontfile=FD+'LiberationSerif-Regular.ttf'); BOLD=pymupdf.Font(fontfile=FD+'LiberationSerif-Bold.ttf'); ITAL=pymupdf.Font(fontfile=FD+'LiberationSerif-Italic.ttf')
ARCH=pymupdf.Archive(FD)
CSS="""@font-face{font-family:LS;src:url(LiberationSerif-Regular.ttf);} @font-face{font-family:LS;font-weight:bold;src:url(LiberationSerif-Bold.ttf);} @font-face{font-family:LS;font-style:italic;src:url(LiberationSerif-Italic.ttf);}
* {font-family:LS; font-size:11.5pt; color:#222222; line-height:1.27;} p{margin:0 0 7pt 0; text-align:justify;} b{font-weight:bold;}"""
INK=(0x22/255,)*3; PURPLE=(0x57/255,0x36/255,0x9a/255); DARK=(0x24/255,0x23/255,0x3a/255)
N_INS=12  # pages insérées après la page imprimée 49
orig=pymupdf.open('orig.pdf'); ch6=pymupdf.open('ch6.pdf'); ch7=pymupdf.open('ch7.pdf')

def wipe(page, rect):
    page.add_redact_annot(rect, fill=(1,1,1)); page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
def html(page, rect, h, scale_low=0.85):
    r=page.insert_htmlbox(rect, h, css=CSS, archive=ARCH, scale_low=scale_low)
    assert r[0]>=0, ('ne tient pas', page.number, h[:60])
    return r
def block_text(page, y0):
    for b in page.get_text('blocks'):
        if abs(b[1]-y0)<1.5: return ' '.join(b[4].split())
    raise Exception(('bloc introuvable', page.number, y0))
def para_html(t): return ''.join(f'<p>{x}</p>' for x in t)
# ---------- 1. textes corrigés
p=orig[1]
r1=block_text(p,119.4); r3=block_text(p,372.4)
r2=block_text(p,230.9).replace("La démarche, strictement qualitative et sans modèle PD/LGD, s'appuie","La démarche des chapitres 1 à 5, qualitative et sans modèle PD/LGD conformément à la fiche projet, s'appuie")
assert r2.startswith('La démarche des chapitres')
add=("Deux chapitres d'ouverture prolongent ce dispositif. Le chapitre 6 adopte la posture de l'analyste risque crédit : sur un portefeuille fictif de 500 M MAD, "
     "des paramètres calibrés sur des données publiques vérifiées (PD annuelle de 1,35 %, LGD de 61 %) donnent des pertes attendues de 9,49 M MAD et des provisions IFRS 9 "
     "de 21,25 M MAD, portées à 37,81 M MAD en récession sévère. Il approfondit aussi les notions du cours : typologie et interdépendance des risques, risque inhérent et résiduel. "
     "Le chapitre 7 présente la plateforme Crédit Horizon Risk Intelligence, qui rend le dispositif opérationnel.")
mk=block_text(p,441.2).replace('Mots-clés :','<b>Mots-clés :</b>').rstrip('.')+' ; perte attendue ; IFRS 9.'
wipe(p, pymupdf.Rect(70,228,530,470))
html(p, pymupdf.Rect(70.9,230.9,527.5,770), para_html([r2,add,r3])+f'<p style="text-align:left">{mk}</p>')
p=orig[2]
a2=block_text(p,215.9).replace("The approach is purely qualitative, with no PD/LGD modelling. It relies","The approach of chapters 1 to 5 is qualitative, with no PD/LGD modelling, as required by the project brief. It relies")
assert 'chapters 1 to 5' in a2
aadd=("Two additional chapters extend this framework. Chapter 6 takes the credit risk analyst's perspective: on a fictional 500 million MAD portfolio, parameters calibrated on verified public data "
      "(annual PD of 1.35%, LGD of 61%) give 12-month expected losses of 9.49 million MAD and IFRS 9 provisions of 21.25 million MAD, rising to 37.81 million MAD under a severe recession. "
      "It also deepens course notions: risk typology and interdependence, inherent and residual risk. Chapter 7 presents the Crédit Horizon Risk Intelligence platform, which makes the framework operational.")
a3=block_text(p,342.4); kw=block_text(p,396.2).replace('Keywords:','<b>Keywords:</b>').rstrip('.')+'; expected loss; IFRS 9.'
wipe(p, pymupdf.Rect(70,213,530,425))
html(p, pymupdf.Rect(70.9,215.9,527.5,770), para_html([a2,aadd,a3])+f'<p style="text-align:left">{kw}</p>')
# Organisation du rapport
p=orig[11]
o=block_text(p,97.4)
o=o.replace('Le rapport comprend cinq chapitres.','Le rapport comprend sept chapitres.').replace("Une conclusion générale répond à la problématique.","Deux chapitres d'ouverture prolongent ce dispositif au-delà de la fiche projet : le chapitre 6 propose une mesure indicative du risque de crédit (PD, LGD, pertes attendues, provisions, stress test) et approfondit les notions du cours ; le chapitre 7 présente la plateforme Crédit Horizon Risk Intelligence. Une conclusion générale répond à la problématique.")
assert 'sept chapitres' in o and 'chapitre 7 présente' in o
wipe(p, pymupdf.Rect(70,95,530,217)); html(p, pymupdf.Rect(70.9,97.4,527.5,770), para_html([o]))
# Hypothèses (p16)
p=orig[15]
h=block_text(p,581.4)+(" Le chapitre 6, ouverture hors fiche, utilise des données publiques externes et un portefeuille fictif présentés comme tels : il ne remet pas en cause H6, puisqu'aucune donnée de Crédit Horizon n'y est utilisée.")
wipe(p, pymupdf.Rect(70,579,530,626)); html(p, pymupdf.Rect(70.9,581.4,527.5,770), para_html([h]))
# 5.7.2 (p58) : remplacer le texte de la puce, garder le symbole
p=orig[57]
def bullet_text_x(page,y0):
    for b in page.get_text('dict')['blocks']:
        if abs(b['bbox'][1]-y0)<1.5:
            xs=[s['bbox'][0] for l in b['lines'] for s in l['spans'] if s['text'].strip() and s['text'].strip()!='•']
            return min(xs)
x=bullet_text_x(p,439.7)
wipe(p, pymupdf.Rect(x-0.5,438,530,483))
html(p, pymupdf.Rect(x-1.0,438.0,527.5,484), para_html(["Compléter la charte par des limites chiffrées fixées par la direction à partir de données réelles ; le chapitre 6 en donne une première illustration (PD, LGD, pertes attendues, stress test), à recalibrer sur l'historique propre de Crédit Horizon."]), scale_low=0.8)
# Conclusion générale, perspectives (p60)
p=orig[59]
wipe(p, pymupdf.Rect(70,333,530,395))
html(p, pymupdf.Rect(70.9,334.9,527.5,770), para_html([
 "Les prolongements naturels sont la qualification juridique de l'organisme, le test de la grille de vérification sur un échantillon de dossiers et la fixation par la direction de limites chiffrées à partir de données réelles (section 5.7).",
 "Le chapitre 6 a ouvert la voie à la mesure : sur un portefeuille fictif de 500 M MAD, des paramètres calibrés sur des données publiques vérifiées donnent des pertes attendues de 9,49 M MAD et des provisions de 21,25 M MAD, portées à 37,81 M MAD en récession sévère. Ces ordres de grandeur sont à recalibrer sur l'historique de Crédit Horizon. Le chapitre 7 a montré comment une plateforme partagée fait vivre le dispositif au quotidien : registre, contrôles, suivi des anomalies et indicateurs tracés, sans jamais automatiser la décision d'octroi. La réponse à la problématique reste la même : la croissance est compatible avec la prudence dès lors qu'elle est arbitrée par des règles explicites, contrôlées et mesurées."]))
# Références (p62)
p=orig[61]
refs=[("Sources complémentaires (chapitres 6 et 7)",None),
 ("Basel Committee on Banking Supervision. (2017). Basel III: Finalising post-crisis reforms. Bank for International Settlements. [Référentiel prudentiel, sous réserve du statut]",1),
 ("ELMENZHI, Z. (2026). Polycopié de Gestion des risques financiers, chapitres 1 et 2. EMSI, 5e année Génie financier. [Cadre du projet]",1),
 ("ELMENZHI, Z. (2026). Polycopié de Contrôle interne, chapitres 1 et 2. EMSI, Génie financier. [Cadre du projet]",1),
 ("Hull, J. C. (2023). Risk management and financial institutions (6e éd.). Wiley. [Ouvrage de référence]",1),
 ("International Accounting Standards Board. (2014). IFRS 9 – Instruments financiers. IFRS Foundation. [Norme comptable, selon le référentiel applicable]",1),
 ("U.S. Small Business Administration. (2026). 7(a) & 504 FOIA data, fichier FOIA_7a_FY2010_FY2019_asof_260930.csv (situation au 30/09/2026). https://data.sba.gov/dataset/7a-504-foia [Données publiques, chapitre 6]",1)]
hh='<h3 style="font-size:15pt;font-weight:bold;color:#24233a;margin:0 0 8pt 0">%s</h3>'%refs[0][0]+''.join(f'<p style="text-align:left;padding-left:25pt;text-indent:-25pt;font-size:11pt">{t}</p>' for t,_ in refs[1:])
html(p, pymupdf.Rect(70.9,520,527.5,770), hh)
# Annexe E (p78)
p=orig[77]
x=bullet_text_x(p,491.3); wipe(p, pymupdf.Rect(x-0.5,489,530,506))
html(p, pymupdf.Rect(x,491.3,527.5,770), para_html(["<b>Données.</b> Aucune donnée réelle de Crédit Horizon n'a été utilisée. Le chapitre 6 s'appuie sur des données publiques américaines (SBA 7(a)) et sur un portefeuille fictif de 500 M MAD, présentés comme tels ; les niveaux de risque résiduel du tableau 6.6 sont des hypothèses."]))

# ---------- 2. numéros de pages des nouveaux chapitres
def find(doc, base, s):
    for i,pg in enumerate(doc):
        if pg.search_for(s): return base+i
    raise Exception(('introuvable', s))
S6=[("6.1 Statut du chapitre et rôle de l'analyste risque crédit","6.1 Statut du chapitre et rôle"),("6.2 Perte attendue, perte inattendue et provisions",None),("6.3 Calibration sur des données publiques vérifiées",None),("6.4 Application à un portefeuille fictif de 500 M MAD",None),("6.5 Stress test et nature des risques",None),("6.6 Typologie et interdépendance des risques",None),("6.7 Risque inhérent, risque résiduel et traitement",None),("6.8 Limites de la mesure",None),("Conclusion du chapitre 6",None)]
S7=[("7.1 Objectifs et principes",None),("7.2 Architecture fonctionnelle",None),("7.3 Parcours d'un dossier et séparation des fonctions","7.3 Parcours d"),("7.4 Données de référence : de la donnée brute au tableau de bord","7.4 Données de référence"),("7.5 Rôles, droits et traçabilité",None),("7.6 Module de révision et logique du contrôle interne","7.6 Module de révision"),("7.7 Limites de la plateforme",None),("Conclusion du chapitre 7",None)]
def sect(doc, base, L):
    out=[]
    for t,k in L:
        key=k or t
        # premier match hors page 1 (liste des sections) sauf si absent
        pages=[i for i,pg in enumerate(doc) if pg.search_for(key)]
        i=pages[-1] if t.startswith('Conclusion') else (pages[1] if len(pages)>1 else pages[0])
        out.append((t, base+i))
    return out
sec6=sect(ch6,51,S6); sec7=sect(ch7,58,S7)
TAB=[("Tableau 6.1 – Profil de l'analyste risque crédit et traduction dans le dispositif",ch6,51),("Tableau 6.2 – PD et LGD de référence selon la garantie et la durée",ch6,51),("Tableau 6.3 – Pertes attendues et provisions IFRS 9 du portefeuille fictif",ch6,51),("Tableau 6.4 – Résultats des scénarios de stress",ch6,51),("Tableau 6.5 – Typologie du cours appliquée à Crédit Horizon",ch6,51),("Tableau 6.6 – Risque inhérent, traitement et risque résiduel visé",ch6,51),("Tableau 7.1 – Modules de la plateforme et livrables correspondants",ch7,58),("Tableau 7.2 – Le modèle des Trois Lignes appliqué à Crédit Horizon",ch7,58)]
TABL=[(t, find(d,b,t.split(' –')[0]+' –')) for t,d,b in TAB]
FIGS=[("Figure 6.1 – De la probabilité de défaut aux provisions et aux fonds propres",ch6,51),("Figure 6.2 – Nœud papillon du risque R03 : contrôles préventifs et détectifs",ch6,51),("Figure 7.1 – Carte mentale du projet et de la plateforme",ch7,58),("Figure 7.2 – Parcours d'un dossier TPE dans la plateforme",ch7,58),("Figure 7.3 – La boucle du contrôle interne appliquée au projet",ch7,58)]
FIGL=[(t, find(d,b,t.split(' –')[0]+' –')) for t,d,b in FIGS]
print(sec6, sec7, TABL, FIGL, sep='\n')
json.dump({'sec6':sec6,'sec7':sec7,'tab':TABL,'fig':FIGL}, open('toc.json','w'), ensure_ascii=False)

# ---------- 3. rendu de lignes de sommaire
LEV={0:(70.9,BOLD,11.5),1:(90.9,REG,11.0),2:(115.9,REG,10.5)}
RIGHT=524.5
def toc_lines(page, y, entries):
    """entries: (level, text, num, gap_before). Retourne y suivant."""
    tw=pymupdf.TextWriter(page.rect, color=INK)
    for lev,text,num,gap in entries:
        x,f,sz=LEV[lev]; y+=gap
        num=str(num); nw=f.text_length(num,sz); dot=f.text_length('.',sz)
        avail=RIGHT-nw-4-x
        words=text.split(' '); lines=[]; cur=''
        for w in words:
            t=(cur+' '+w).strip()
            if f.text_length(t,sz)>avail-15 and cur: lines.append(cur); cur=w
            else: cur=t
        lines.append(cur)
        for j,ln in enumerate(lines):
            base=y+0.891*sz
            tw.append((x,base),ln,font=f,fontsize=sz)
            if j==len(lines)-1:
                end=x+f.text_length(ln,sz)+2; nd=int((RIGHT-nw-2-end)/dot)
                if nd>0: tw.append((RIGHT-nw-2-nd*dot,base),'.'*nd,font=f,fontsize=sz)
                tw.append((RIGHT-nw,base),num,font=f,fontsize=sz)
            y+=14.0 if lev else 14.4
    tw.write_text(page)
    return y
def body_wipe(page, y0, y1=780): wipe(page, pymupdf.Rect(60,y0,540,y1))

late=lambda n: n+N_INS
# Sommaire p5/p6
p=orig[4]; body_wipe(p,714,775)
p=orig[5]; body_wipe(p,65,780)
E=[(0,'Chapitre 6 : Ouverture : mesure du risque de crédit et approfondissements',50,0)]+[(1,t,n,0) for t,n in sec6[:-1]]
E+=[(0,'Chapitre 7 : La plateforme Crédit Horizon Risk Intelligence',57,6)]+[(1,t,n,0) for t,n in sec7[:-1]]
E+=[(0,'Conclusion générale',late(50),6),(0,'Références bibliographiques',late(52),6),(0,'Table des matières détaillée',late(54),6),(0,'Annexes',late(57),6)]
E+=[(1,'Annexe A – Registre détaillé des risques',late(58),0),(1,'Annexe B – Fiches des contrôles organisationnels',late(61),0),(1,'Annexe C – Diagnostic par principe COSO',late(66),0),(1,'Annexe D – Check-list de conformité à la fiche',late(68),0),(1,'Annexe E – Limites du travail et points à vérifier',late(69),0)]
toc_lines(p,72,E)
# Table des matières détaillée p64/p65
p=orig[63]; body_wipe(p,712,775)
p=orig[64]; body_wipe(p,65,780)
E=[(0,'Chapitre 6 : Ouverture : mesure du risque de crédit et approfondissements',50,0)]+[(1 if not t.startswith('Conclusion') else 2,t,n,0) for t,n in sec6]
E+=[(0,'Chapitre 7 : La plateforme Crédit Horizon Risk Intelligence',57,6)]+[(1 if not t.startswith('Conclusion') else 2,t,n,0) for t,n in sec7]
E+=[(0,'Conclusion générale',late(50),6),(0,'Références bibliographiques',late(52),6),(0,'Table des matières détaillée',late(54),6),(0,'Annexes',late(57),6),(1,'Annexe A – Registre détaillé des risques',late(58),0),(1,'Annexe B – Fiches des contrôles organisationnels',late(61),0)]
E+=[(2,t,late(n),0) for t,n in [("C01 – Contrôle de complétude des dossiers",61),("C02 – Double validation des décisions de crédit",62),("C03 – Séparation des fonctions commerciales, de risques et d'autorisation",62),("C04 – Suivi des anomalies et des dérogations",63),("C05 – Surveillance des retards et de la liquidité",63),("C06 – Revue périodique de la qualité du portefeuille",64),("C07 – Suivi de la concentration du portefeuille",64),("C08 – Contrôle du reporting",65)]]
E+=[(1,'Annexe C – Diagnostic par principe COSO',late(66),0),(1,'Annexe D – Check-list de conformité à la fiche',late(68),0),(1,'Annexe E – Limites du travail et points à vérifier',late(69),0)]
yend=toc_lines(p,72,E); assert yend<780, yend
# Liste des figures p7
p=orig[6]; toc_lines(p,240.4+0.2,[(1,t,n,0) for t,n in FIGL])
# Liste des tableaux : p8 jusqu'à 5.17, puis nouveaux tableaux, puis A–D sur une page de suite
p=orig[7]; body_wipe(p,605,775)
yy=toc_lines(p,607.2,[(1,t,n,0) for t,n in TABL[:8]])
ANN=[("Tableau A.1 – Registre détaillé des risques",58),("Tableau B.1 – Fiche du contrôle C01",61),("Tableau B.2 – Fiche du contrôle C02",62),("Tableau B.3 – Fiche du contrôle C03",62),("Tableau B.4 – Fiche du contrôle C04",63),("Tableau B.5 – Fiche du contrôle C05",63),("Tableau B.6 – Fiche du contrôle C06",64),("Tableau B.7 – Fiche du contrôle C07",64),("Tableau B.8 – Fiche du contrôle C08",65),("Tableau C.1 – Diagnostic provisoire des dix-sept principes COSO",66),("Tableau D.1 – Check-list de conformité à la fiche projet",68)]
print('fin liste tableaux p8', yy)

# ---------- 4. pages de garde
def cover(num, lines):
    d=pymupdf.open(); d.insert_pdf(orig, from_page=43, to_page=43); pg=d[0]
    wipe(pg, pymupdf.Rect(150,290,450,440)); wipe(pg, pymupdf.Rect(140,490,460,590))
    tw=pymupdf.TextWriter(pg.rect, color=PURPLE)
    w=BOLD.text_length(num,125); tw.append((297.6-w/2,297.5+0.891*125),num,font=BOLD,fontsize=125); tw.write_text(pg)
    tw=pymupdf.TextWriter(pg.rect, color=DARK)
    for i,l in enumerate(lines):
        w=BOLD.text_length(l,24); tw.append((297.6-w/2,496.6+0.891*24+i*27.6),l,font=BOLD,fontsize=24)
    tw.write_text(pg); return d
c6=cover('6',['Ouverture : mesure du','risque de crédit et','approfondissements']); c7=cover('7',['La plateforme Crédit','Horizon Risk Intelligence'])

# ---------- 5. renumérotation des pages après l'insertion
def renum(page, old, new):
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if s['bbox'][1]>790 and s['text'].strip()==old:
                    r=pymupdf.Rect(s['bbox']); wipe(page, r+(-2,-1,2,1))
                    tw=pymupdf.TextWriter(page.rect, color=INK); w=REG.text_length(new,11.5)
                    tw.append(((r.x0+r.x1)/2-w/2, s['origin'][1]), new, font=REG, fontsize=11.5); tw.write_text(page); return True
    return False
for i in range(58,78):
    pg=orig[i]; t=[s['text'].strip() for b in pg.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['bbox'][1]>790]
    if t and t[0].isdigit(): assert renum(pg, t[0], str(int(t[0])+N_INS)), i
assert renum(orig[8],'viii','ix')

# ---------- 6. page de suite de la liste des tableaux
sup=pymupdf.open(); sup.insert_pdf(orig, from_page=7, to_page=7); sp=sup[0]
body_wipe(sp,60,780); wipe(sp, pymupdf.Rect(290,790,310,812))
tw=pymupdf.TextWriter(sp.rect, color=INK); w=REG.text_length('viii',11.5); tw.append((297.6-w/2,798.2+0.891*11.5),'viii',font=REG,fontsize=11.5); tw.write_text(sp)
# restaurer l'en-tête italique (effacé par body_wipe ? non : l'en-tête est au-dessus de 60)
toc_lines(sp,72,[(1,t,late(n),0) for t,n in ANN])

# ---------- 7. assemblage
out=pymupdf.open()
out.insert_pdf(orig, from_page=0, to_page=7)
out.insert_pdf(sup)
out.insert_pdf(orig, from_page=8, to_page=57)
out.insert_pdf(c6); out.insert_pdf(ch6); out.insert_pdf(c7); out.insert_pdf(ch7)
out.insert_pdf(orig, from_page=58, to_page=77)
out.set_metadata({**orig.metadata, 'title':'Crédit Horizon – Rapport de projet (version mise à jour)'})
out.save('/home/user/fatima-portfolio/Credit_Horizon_Rapport_Academique_mis_a_jour.pdf', garbage=3, deflate=True)
print('pages', out.page_count)
