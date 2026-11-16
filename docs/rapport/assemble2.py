import pymupdf, re, json
FD='/usr/share/fonts/truetype/liberation/'
REG=pymupdf.Font(fontfile=FD+'LiberationSerif-Regular.ttf'); BOLD=pymupdf.Font(fontfile=FD+'LiberationSerif-Bold.ttf')
ARCH=pymupdf.Archive(FD)
CSS="""@font-face{font-family:LS;src:url(LiberationSerif-Regular.ttf);} @font-face{font-family:LS;font-weight:bold;src:url(LiberationSerif-Bold.ttf);} @font-face{font-family:LS;font-style:italic;src:url(LiberationSerif-Italic.ttf);}
* {font-family:LS; font-size:11.5pt; color:#222222; line-height:1.27;} p{margin:0 0 7pt 0; text-align:justify;} b{font-weight:bold;}"""
INK=(0x22/255,)*3
orig=pymupdf.open('orig.pdf'); annF=pymupdf.open('annF.pdf'); annG=pymupdf.open('annG.pdf')
F0=70; G0=F0+annF.page_count

def wipe(page, rect, fill=(1,1,1)):
    page.add_redact_annot(rect, fill=fill); page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
def html(page, rect, h, scale_low=0.85, css=CSS):
    r=page.insert_htmlbox(rect, h, css=css, archive=ARCH, scale_low=scale_low)
    assert r[0]>=0, ('ne tient pas', page.number, h[:60]); return r
def block(page, y0):
    for b in page.get_text('blocks'):
        if abs(b[1]-y0)<1.5: return ' '.join(b[4].split())
    raise Exception(('bloc', page.number, y0))
def ph(t): return ''.join(f'<p>{x}</p>' for x in t)
def bullet_x(page,y0):
    for b in page.get_text('dict')['blocks']:
        if abs(b['bbox'][1]-y0)<1.5:
            return min(s['bbox'][0] for l in b['lines'] for s in l['spans'] if s['text'].strip() and s['text'].strip()!='•')

# --- Organisation du rapport (p12) : annexes F et G
p=orig[11]; o=block(p,97.4)
assert o.endswith('limites du travail.')
o=o[:-1]+", la correspondance entre les notions des cours et le rapport (annexe F) et, à titre facultatif, une mesure indicative du risque de crédit qui dépasse le périmètre de la fiche (annexe G)."
wipe(p, pymupdf.Rect(70,95,530,217)); html(p, pymupdf.Rect(70.9,97.4,527.5,770), ph([o]))
# --- Hypothèses (p16)
p=orig[15]; h=block(p,581.4)+" L'annexe G, facultative et hors fiche, utilise des données publiques externes et un portefeuille fictif présentés comme tels ; elle ne remet pas en cause H6, puisqu'aucune donnée de Crédit Horizon n'y est utilisée."
wipe(p, pymupdf.Rect(70,579,530,626)); html(p, pymupdf.Rect(70.9,581.4,527.5,770), ph([h]))
# --- 5.7.2 (p58)
p=orig[57]; x=bullet_x(p,439.7); wipe(p, pymupdf.Rect(x-0.5,438,530,483))
html(p, pymupdf.Rect(x-1.0,438.0,527.5,484), ph(["Compléter la charte par des limites chiffrées fixées par la direction à partir de données réelles ; une modélisation quantitative (PD, LGD) pourrait alors être envisagée. L'annexe G en donne, à titre facultatif, une première illustration."]), scale_low=0.8)
# --- Conclusion générale, perspectives (p60)
p=orig[59]; c=block(p,334.9)
wipe(p, pymupdf.Rect(70,333,530,395))
html(p, pymupdf.Rect(70.9,334.9,527.5,770), ph([c, "À titre facultatif, l'annexe G esquisse cette mesure sur un portefeuille fictif de 500 M MAD : des paramètres calibrés sur des données publiques vérifiées y donnent des pertes attendues de 9,49 M MAD et des provisions de 21,25 M MAD, portées à 37,81 M MAD en récession sévère. Ces ordres de grandeur, purement indicatifs, ne modifient pas la réponse qualitative apportée à la problématique."]))
# --- Annexe E (p78)
p=orig[77]; x=bullet_x(p,491.3); wipe(p, pymupdf.Rect(x-0.5,489,530,506))
html(p, pymupdf.Rect(x,491.3,527.5,770), ph(["<b>Données.</b> Aucune donnée réelle ou fictive chiffrée sur Crédit Horizon n'a été utilisée dans les chapitres 1 à 5. L'annexe G, facultative, s'appuie sur des données publiques américaines (SBA 7(a)) et sur un portefeuille fictif de 500 M MAD, présentés comme tels."]))
# --- Annexe D : note (p77)
html(orig[76], pymupdf.Rect(70.9,700,527.5,770), ph(["<b>Compléments facultatifs.</b> L'annexe F (correspondance avec les cours) et l'annexe G (mesure indicative du risque de crédit, hors fiche) ne modifient pas les livrables exigés, qui restent qualitatifs et sans modèle PD/LGD."]))
# --- Sigles (p9)
sig=[('EAD','Exposure at Default (exposition au moment du défaut)'),('EL','Expected Loss (perte attendue)'),('HHI','Indice de Herfindahl-Hirschman (concentration)'),('IFRS 9','Norme comptable sur les instruments financiers'),('SBA','U.S. Small Business Administration (source des données de l\'annexe G)')]
html(orig[8], pymupdf.Rect(70.9,560,527.5,770), '<p style="font-size:10.5pt;font-weight:bold;color:#24233a;margin-bottom:4pt">Sigles de l\'annexe G</p>'+''.join(f'<p style="font-size:10.5pt;text-align:left;margin:0 0 2pt 0"><b>{a}</b> : {b}</p>' for a,b in sig))
# --- Annexe A : mesures de contrôle associées (cohérence avec le tableau 5.3 et les fiches B)
FIX={'R01':"C01 – Contrôle de complétude indépendant avant passage en décision ; C04 – Registre des anomalies et dérogations",
     'R03':"C06 – Revue de qualité du portefeuille et objectifs commerciaux incluant la qualité ; C07 – Suivi de la concentration ; C02 – Double validation ; C03 – Séparation des fonctions",
     'R06':"C05 – Suivi de la liquidité ; Charte d'appétence (section 5.1)"}
done=set()
for pn in [67,68,69]:
    pg=orig[pn-1]
    for tb in pg.find_tables().tables:
        for r in tb.rows:
            cells=r.cells; txt=pg.get_textbox(pymupdf.Rect(cells[0])).strip() if cells[0] else ''
            if txt in FIX and txt not in done:
                rect=pymupdf.Rect(cells[-1]); old=pg.get_text('dict', clip=rect)
                sz=[s['size'] for b in old['blocks'] for l in b.get('lines',[]) for s in l['spans']]
                fs=min(sz) if sz else 8
                wipe(pg, rect+(1,1,-1,-1), fill=False)
                html(pg, rect+(2.5,2,-2,-1), f'<p style="font-size:{fs}pt;text-align:left;line-height:1.55">{FIX[txt]}</p>', scale_low=0.6)
                done.add(txt)
assert done==set(FIX), done
# --- Bibliographie : mentions réglementaires prudentes
TAGS=[('[Obligation réglementaire, si Crédit Horizon relève de la loi bancaire]','[À examiner si Crédit Horizon relève de la loi bancaire ; intitulé et date vérifiés, texte intégral non lu]'),
      ('[Obligation réglementaire, si le statut s\'applique]','[À examiner si le statut d\'établissement de crédit est confirmé]'),
      ('[Obligation réglementaire sectorielle, sous réserve du statut]','[Texte sectoriel à examiner sous réserve du statut ; non lu intégralement]')]
n_tags=0
for pn in [61,62]:
    pg=orig[pn-1]
    lines=[]
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines',[]): lines.append((l['bbox'], ''.join(s['text'] for s in l['spans']), l['spans'][-1]))
    for i,(bb,t,sp) in enumerate(lines):
        if '[Obligation' not in t: continue
        j=i; full=t[t.index('[Obligation'):]
        while ']' not in full: j+=1; full+=lines[j][1]
        full=' '.join(full.split()).replace('[ Obligation','[Obligation')
        new=[n for o,n in TAGS if ' '.join(o.split())==full.strip()]
        if not new:
            # cas « [Obligation » en fin de ligne puis suite
            new=[n for o,n in TAGS if full.strip().startswith(o[:22]) and o.split()[-1]==full.split()[-1]]
        assert new, full
        x0=pg.search_for('[Obligation', clip=pymupdf.Rect(bb))[0].x0
        size=sp['size']
        wipe(pg, pymupdf.Rect(x0-0.5, bb[1], 530, bb[3]))
        for k in range(i+1,j+1): wipe(pg, pymupdf.Rect(lines[k][0][0]-0.5, lines[k][0][1], 530, lines[k][0][3]))
        # réécriture : reste de la 1re ligne puis ligne(s) suivante(s)
        words=new[0].split(' '); cur=''; out=[]; avail=527.5-x0; first=True
        for w in words:
            t2=(cur+' '+w).strip()
            if REG.text_length(t2,size)>avail and cur: out.append((first,cur)); cur=w; first=False; avail=527.5-lines[i+1][0][0]
            else: cur=t2
        out.append((first,cur))
        tw=pymupdf.TextWriter(pg.rect, color=INK); y=sp['origin'][1]; k=0
        for fst,txt in out:
            xx=x0 if fst else lines[i+1][0][0]
            yy=y if fst else lines[min(i+1+k,j)][2]['origin'][1] if i+1+k<=j else y+14*(k+1)
            tw.append((xx,yy),txt,font=REG,fontsize=size)
            if not fst: k+=1
        tw.write_text(pg); n_tags+=1
print('mentions réglementaires corrigées :', n_tags)
# Tableaux 2.3 et 2.5 : intitulés
pg=orig[21]; wipe(pg, pymupdf.Rect(74,110,135,135), fill=False)
html(pg, pymupdf.Rect(75.2,110,140,140), '<p style="font-size:9pt;font-weight:bold;color:#24233a;text-align:left;line-height:1.2">Textes réglementaires (selon le statut)</p>', scale_low=0.8)
pg=orig[22]
wipe(pg, pymupdf.Rect(175,443,266,483), fill=False)
html(pg, pymupdf.Rect(176.9,444.5,266,484), '<p style="font-size:9pt;text-align:left;line-height:1.25">Textes réglementaires applicables selon le statut</p>', scale_low=0.8)
# --- Sommaires et listes
def sect(doc, base, L):
    out=[]
    for t in L:
        pages=[i for i,pg in enumerate(doc) if pg.search_for(t[:28])]
        i=pages[-1] if t.startswith('Conclusion') else (pages[1] if len(pages)>1 else pages[0])
        out.append((t, base+i))
    return out
SG=["G.1 Statut de l'annexe et rôle de l'analyste risque crédit","G.2 Perte attendue, perte inattendue et provisions","G.3 Calibration sur des données publiques vérifiées","G.4 Application à un portefeuille fictif de 500 M MAD","G.5 Stress test et nature des risques","G.6 Typologie et interdépendance des risques","G.7 Risque inhérent, risque résiduel et traitement","G.8 Limites de la mesure"]
secG=sect(annG,G0,SG)
def find(doc,base,s):
    for i,pg in enumerate(doc):
        if pg.search_for(s): return base+i
    raise Exception(s)
TABG=[(t, find(annG,G0,t.split(' –')[0]+' –')) for t in ["Tableau G.1 – Profil de l'analyste risque crédit et traduction dans le dispositif","Tableau G.2 – PD et LGD de référence selon la garantie et la durée","Tableau G.3 – Pertes attendues et provisions IFRS 9 du portefeuille fictif","Tableau G.4 – Résultats des scénarios de stress","Tableau G.5 – Typologie du cours appliquée à Crédit Horizon","Tableau G.6 – Risque inhérent, traitement et risque résiduel visé"]]
FIGG=[(t, find(annG,G0,t.split(' –')[0]+' –')) for t in ["Figure G.1 – De la probabilité de défaut aux provisions et aux fonds propres","Figure G.2 – Nœud papillon du risque R03 : contrôles préventifs et détectifs"]]
print(secG, TABG, FIGG, sep='\n')
LEV={0:(70.9,BOLD,11.5),1:(90.9,REG,11.0),2:(115.9,REG,10.5)}
def toc_lines(page, y, entries):
    tw=pymupdf.TextWriter(page.rect, color=INK)
    for lev,text,num,gap in entries:
        x,f,sz=LEV[lev]; y+=gap; num=str(num); nw=f.text_length(num,sz); dot=f.text_length('.',sz)
        avail=524.5-nw-4-x; lines=[]; cur=''
        for w in text.split(' '):
            t=(cur+' '+w).strip()
            if f.text_length(t,sz)>avail-15 and cur: lines.append(cur); cur=w
            else: cur=t
        lines.append(cur)
        for j,ln in enumerate(lines):
            base=y+0.891*sz; tw.append((x,base),ln,font=f,fontsize=sz)
            if j==len(lines)-1:
                end=x+f.text_length(ln,sz)+2; nd=int((524.5-nw-2-end)/dot)
                if nd>0: tw.append((524.5-nw-2-nd*dot,base),'.'*nd,font=f,fontsize=sz)
                tw.append((524.5-nw,base),num,font=f,fontsize=sz)
            y+=14.0
    tw.write_text(page); return y
def last_line_bottom(page, label):
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            if ''.join(s['text'] for s in l['spans']).startswith(label): return l['bbox'][1]
    raise Exception(label)
# Sommaire (p6) et table détaillée (p65) : ajout des annexes F et G après l'annexe E
for pi,detail in [(5,False),(64,True)]:
    pg=orig[pi]; y=last_line_bottom(pg,'Annexe E')+14.0
    E=[(1,'Annexe F – Correspondance entre les cours et le rapport',F0,0),(1,'Annexe G – Ouverture facultative : mesure indicative du risque de crédit',G0,0)]
    if detail: E+= [(2,t,n,0) for t,n in secG]
    toc_lines(pg,y,E)
# Liste des figures (p7)
toc_lines(orig[6],240.6,[(1,t,n,0) for t,n in FIGG])
# Liste des tableaux : page de suite
sup=pymupdf.open(); sup.insert_pdf(orig, from_page=7, to_page=7); sp=sup[0]
wipe(sp, pymupdf.Rect(60,60,540,780)); wipe(sp, pymupdf.Rect(280,790,320,812))
tw=pymupdf.TextWriter(sp.rect, color=INK); w=REG.text_length('viii',11.5); tw.append((297.6-w/2,798.2+0.891*11.5),'viii',font=REG,fontsize=11.5); tw.write_text(sp)
toc_lines(sp,72,[(1,"Tableau F.1 – Notions des cours, application au cas et sections du rapport",F0,0)]+[(1,t,n,0) for t,n in TABG])
def renum(page, old, new):
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if s['bbox'][1]>790 and s['text'].strip()==old:
                    r=pymupdf.Rect(s['bbox']); wipe(page, r+(-2,-1,2,1))
                    tw=pymupdf.TextWriter(page.rect, color=INK); w=REG.text_length(new,11.5)
                    tw.append(((r.x0+r.x1)/2-w/2, s['origin'][1]), new, font=REG, fontsize=11.5); tw.write_text(page); return True
assert renum(orig[8],'viii','ix')
# --- assemblage
out=pymupdf.open()
out.insert_pdf(orig, from_page=0, to_page=7); out.insert_pdf(sup); out.insert_pdf(orig, from_page=8, to_page=77)
out.insert_pdf(annF); out.insert_pdf(annG)
out.set_metadata({**orig.metadata, 'title':'Crédit Horizon – Rapport de projet'})
out.save('/home/user/fatima-portfolio/Credit_Horizon_Rapport_Academique_mis_a_jour.pdf', garbage=3, deflate=True)
print('pages', out.page_count)
