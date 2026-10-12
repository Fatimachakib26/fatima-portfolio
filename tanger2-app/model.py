"""
Moteur financier « Tanger II » — réplique Python simplifiée du modèle Excel
(01_Modele_financier_Tanger_II.xlsx, 24 onglets).

Horizon : 2027 → 2038 (12 exercices), MDH hors taxes.
Dette et crédit-bail calculés au pas semestriel puis agrégés par année.

Les hypothèses reprennent l'onglet 02_Hypotheses. Le moteur est volontairement
autonome (numpy uniquement) pour être appelé des milliers de fois par la
simulation de Monte-Carlo et l'optimiseur.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
import numpy as np

YEARS = np.arange(2027, 2039)
N = len(YEARS)
NS = 2 * N  # semestres

# ---------------------------------------------------------------------------
# Hypothèses (onglet 02)
# ---------------------------------------------------------------------------
RAMP = [0.50, 0.72, 0.85, 0.90, 0.92]          # R01 : utilisation par année d'exploitation
STARTUP_OVERCOST = [0.05, 0.02, 0.0, 0.0, 0.0]  # R02

# K01..K11 : (libellé, montant, taux d'amort., part décaissée S1-27, S2-27, S1-28, S2-28)
CAPEX_ITEMS = [
    ("Terrain", 46, 0.00, (1.00, 0.00, 0.00, 0.00), False),
    ("Aménagement / VRD", 14, 0.05, (0.60, 0.40, 0.00, 0.00), True),
    ("Bâtiments", 180, 0.05, (0.30, 0.40, 0.25, 0.05), True),
    ("Installations techniques", 64, 0.10, (0.00, 0.35, 0.50, 0.15), True),
    ("Machines de production", 355, 0.10, (0.10, 0.30, 0.45, 0.15), True),
    ("Équipements logistiques", 28, 0.15, (0.00, 0.00, 0.60, 0.40), True),
    ("Systèmes d'information", 16, 0.20, (0.00, 0.30, 0.40, 0.30), True),
    ("Mobilier / véhicules", 6, 0.20, (0.00, 0.00, 0.50, 0.50), True),
    ("Ingénierie / mise en service", 30, 0.10, (0.10, 0.30, 0.40, 0.20), True),
    ("Frais préopérationnels", 22, 0.20, (0.10, 0.20, 0.40, 0.30), False),
    ("Provision pour aléas", 30, 0.10, (0.10, 0.30, 0.40, 0.20), True),
]
CAPEX_BASE = sum(i[1] for i in CAPEX_ITEMS)               # 791
ELIGIBLE_BASE = sum(i[1] for i in CAPEX_ITEMS if i[4])    # 723 (hors terrain & préop.)
MAINT_BASE = 355 + 64 + 28                                # machines + install. + logistique


@dataclass
class Shocks:
    """Chocs et mesures correctrices (table des cas, onglet 02 section 11)."""
    capex_overrun: float = 0.0      # C01
    delay_months: float = 0.0       # C02
    price: float = 0.0              # C03
    volume: float = 0.0             # C04 (points d'utilisation relatifs)
    materials: float = 0.0          # C05
    energy: float = 0.0             # C06
    ebitda_margin: float = 0.0      # C07 (points de CA)
    rate: float = 0.0               # C08
    dso_days: float = 0.0           # C09
    prime_obtained: float = 1.0     # C10
    extra_equity: float = 0.0       # C11 mesure
    standby_debt: float = 0.0       # C12 mesure
    extra_grace: int = 0            # C13 mesure (semestres)
    extra_tenor: int = 0            # C14 mesure (semestres)
    deferred_capex: float = 0.0     # C15 mesure (MDH reportés en 2033)


@dataclass
class Financing:
    """Structure de financement (onglet 02 section 10)."""
    name: str = "B"
    equity: float = 350.0
    debt: float = 450.0
    lease: float = 180.0
    debt_rate: float = 0.0525
    grace_sem: int = 6
    n_repay_sem: int = 14
    annuity: bool = True           # F07 : 2 = annuités constantes
    arrangement_fee: float = 0.01
    lease_rate: float = 0.065
    lease_sem: int = 14
    lease_residual: float = 0.01
    prime_rate: float = 0.0        # F12
    bridge_share: float = 0.0      # F13
    bridge_spread: float = -0.0025 # F14
    tax_holiday: bool = False      # F15


@dataclass
class Market:
    """Coût du capital et valeur terminale (section 7)."""
    rf: float = 0.0355
    beta_u: float = 1.20
    mrp: float = 0.067
    specific_premium: float = 0.0
    tv_method: int = 1             # 1 = VNC + BFR ; 2 = Gordon ; 3 = multiple
    growth: float = 0.015
    exit_multiple: float = 5.0
    tax_shield: float = 0.35


SCENARIOS = {
    "A": Financing("A — FP + dette", 440, 540, 0, lease_rate=0.0),
    "B": Financing("B — FP + dette + crédit-bail", 350, 450, 180),
    "C": Financing("C — Mixte avec aides", 320, 420, 180, prime_rate=0.11,
                   bridge_share=0.8, tax_holiday=True),
}

CASES = {
    "1. Central": Shocks(),
    "2. Prudent": Shocks(capex_overrun=0.05, price=-0.01, volume=-0.05, materials=0.01,
                         energy=0.10, rate=0.005, dso_days=10),
    "3. Favorable": Shocks(capex_overrun=-0.03, price=0.01, volume=0.03, materials=-0.01,
                           energy=-0.05, rate=-0.0025),
    "4. Stress CAPEX +20 %": Shocks(capex_overrun=0.20),
    "5. Stress retard 6 mois": Shocks(delay_months=6),
    "6. Stress combiné": Shocks(capex_overrun=0.20, delay_months=6),
    "7. Combiné + mesures": Shocks(capex_overrun=0.20, delay_months=6, extra_equity=90,
                                   standby_debt=70, deferred_capex=25, extra_grace=2),
    "8. Sans prime (C)": Shocks(prime_obtained=0.0),
}

MIN_CASH = 40.0
DSCR_COVENANT = 1.20
LEV_COVENANT = 3.5
EQUITY_CAPACITY = 350.0
BANK_CAP = 540.0


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------
def irr(flows) -> float:
    """TRI par bissection robuste (renvoie nan si pas de changement de signe)."""
    f = np.asarray(flows, dtype=float)
    t = np.arange(len(f))

    def npv(r):
        return np.sum(f / (1 + r) ** t)

    lo, hi = -0.95, 3.0
    vlo, vhi = npv(lo), npv(hi)
    if np.sign(vlo) == np.sign(vhi):
        return float("nan")
    for _ in range(100):
        mid = (lo + hi) / 2
        vm = npv(mid)
        if np.sign(vm) == np.sign(vlo):
            lo, vlo = mid, vm
        else:
            hi = mid
        if hi - lo < 1e-7:
            break
    return (lo + hi) / 2


def _annuity(pv, r, n):
    if n <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return pv / n
    return pv * r / (1 - (1 + r) ** -n)


def _utilization(delay_years: float):
    """Taux d'utilisation moyen, de fin d'année et fraction en exploitation par année civile.

    Mise en service prévue au 01/07/2028 (t = 1,5 an depuis le 01/01/2027), décalée du retard.
    Formule Excel : u(k) = (1 − f)·R(k − q) + f·R(k − q − 1).
    """
    start = 1.5 + delay_years
    start_plan = 1.5

    def R(j):
        if j < 1:
            return 0.0
        return RAMP[min(j, len(RAMP)) - 1]

    def rate_at(t):  # utilisation instantanée au temps t
        if t <= start:
            return 0.0
        return R(int(np.ceil(t - start - 1e-9)))

    avg, end, frac, frac_plan, oc = (np.zeros(N) for _ in range(5))
    # intégration numérique au pas mensuel
    for k in range(N):
        ts = k + (np.arange(12) + 0.5) / 12
        rates = np.array([rate_at(t) for t in ts])
        avg[k] = rates.mean()
        end[k] = rate_at(k + 1 - 1e-6)
        frac[k] = np.clip(k + 1 - start, 0, 1)
        frac_plan[k] = np.clip(k + 1 - start_plan, 0, 1)
        ocs = []
        for t in ts:
            if t > start:
                j = int(np.ceil(t - start - 1e-9))
                ocs.append(STARTUP_OVERCOST[min(j, 5) - 1])
            else:
                ocs.append(0.0)
        oc[k] = np.mean(ocs)
    return avg, end, frac, frac_plan, oc, start


# ---------------------------------------------------------------------------
# Moteur
# ---------------------------------------------------------------------------
def run(fin: Financing, sh: Shocks | None = None, mk: Market | None = None) -> dict:
    sh = sh or Shocks()
    mk = mk or Market()
    delay_y = sh.delay_months / 12.0
    avg_u, end_u, frac, frac_plan, oc_avg, start_t = _utilization(delay_y)
    vol_factor = 1 + sh.volume
    k_idx = np.maximum(np.arange(N) - 1, 0)  # années d'indexation depuis 2028

    cap = 500_000
    vol = cap * avg_u * vol_factor
    vol_end = cap * end_u * vol_factor
    price = 3500 * (1 - 0.005) ** k_idx * (1 + sh.price)
    mat_u = 2188 * (1 - 0.005) ** k_idx * (1 + sh.materials)
    ene_u = 115 * 1.02 ** k_idx * (1 + sh.energy)
    dl_u = 108 * 1.015 ** k_idx

    ca = vol * price / 1e6
    mat = vol * mat_u * (1 + oc_avg) / 1e6
    ene = vol * ene_u / 1e6
    dl = vol * dl_u * (1 + oc_avg) / 1e6
    logi = 0.035 * ca
    other = 0.015 * ca
    var_costs = mat + ene + dl + logi + other

    fixed_coef = frac + 0.7 * np.maximum(frac_plan - frac, 0)
    capex_mult = 1 + sh.capex_overrun
    pers = 60 * 1.035 ** k_idx * fixed_coef
    ga = 52 * 1.02 ** k_idx * fixed_coef
    maint = 0.02 * MAINT_BASE * capex_mult * 1.02 ** k_idx * fixed_coef
    fixed = pers + ga + maint
    ebitda = ca - var_costs - fixed + sh.ebitda_margin * ca

    # ---- CAPEX (semestres S1-27..S2-28) -------------------------------------
    capex_sem = np.zeros(NS)
    for _, amt, _, split, _ in CAPEX_ITEMS:
        for s, p in enumerate(split):
            capex_sem[s] += amt * capex_mult * p
    deferred = min(sh.deferred_capex, capex_sem[3])
    capex_sem[3] -= deferred
    capex_init = capex_sem.reshape(N, 2).sum(1)
    capex_init[6] += deferred  # réalisés en 2033 (H08)
    renew = np.where(YEARS >= 2031, 0.015 * ca, 0.0)
    capex_total = capex_init + renew

    # ---- Amortissements (base tout acquis) ----------------------------------
    dep = np.zeros(N)
    for _, amt, rate, _, _ in CAPEX_ITEMS:
        base = amt * capex_mult
        if rate == 0:
            continue
        remaining = base
        for k in range(N):
            d = min(remaining, base * rate * frac[k])
            dep[k] += d
            remaining -= d
    dep[6:] += deferred * 0.10
    ren_stock = 0.0
    for k in range(N):
        dep[k] += 0.10 * ren_stock
        ren_stock += renew[k]

    # ---- BFR -----------------------------------------------------------------
    ca_rr = cap * end_u * vol_factor * price / 1e6
    mat_rr = cap * end_u * vol_factor * mat_u * (1 + oc_avg) / 1e6
    purch_rr = mat_rr + cap * end_u * vol_factor * ene_u / 1e6 + 0.05 * ca_rr
    prod_rr = mat_rr + cap * end_u * vol_factor * (ene_u + dl_u) / 1e6 + np.where(end_u > 0, fixed / np.maximum(fixed_coef, 1e-9), 0)
    pers_rr = cap * end_u * vol_factor * dl_u / 1e6 + np.where(end_u > 0, 60 * 1.035 ** k_idx, 0)
    bfr = ((60 + sh.dso_days) / 360 * ca_rr + 30 / 360 * mat_rr + 12 / 360 * prod_rr
           - 60 / 360 * purch_rr - 20 / 360 * pers_rr)
    dbfr = np.diff(np.concatenate([[0.0], bfr]))

    # ---- Fiscalité théorique (flux non endettés) -----------------------------
    def corporate_tax(pretax, holiday: bool):
        tax = np.zeros(N)
        loss_cf = 0.0
        under = 99  # exercices consécutifs sous le seuil (99 = jamais franchi)
        op_rank = 0
        for k in range(N):
            if frac[k] > 0:
                op_rank += 1
            base = pretax[k]
            if base < 0:
                loss_cf += -base
                taxable = 0.0
            else:
                used = min(loss_cf, base)
                loss_cf -= used
                taxable = base - used
            # art. 19 CGI : 35 % sur la totalité dès 100 MDH ; retour à 20 % après 3 exercices sous le seuil
            under = 0 if taxable >= 100 else under + 1
            rate = 0.35 if under < 3 else 0.20
            is_th = taxable * rate
            cm = 0.0025 * ca[k] if op_rank >= 4 else 0.0
            exempt = holiday and 1 <= op_rank <= 5
            tax[k] = 0.0 if exempt else max(is_th, cm)
        return tax

    ebit_u = ebitda - dep
    tax_u = corporate_tax(ebit_u, False)
    tax_u_hol = corporate_tax(ebit_u, True)

    # ---- Financement : dette, crédit-bail, relais -----------------------------
    r = fin.debt_rate + sh.rate
    rs = r / 2
    on_bs_capex = capex_sem.copy()
    lease_val = fin.lease * capex_mult if fin.lease > 0 else 0.0
    on_bs_capex[2] -= lease_val * 0.6
    on_bs_capex[3] -= lease_val * 0.4
    on_bs_capex = np.maximum(on_bs_capex, 0)
    need_profile = on_bs_capex[:4] / on_bs_capex[:4].sum()

    equity_total = fin.equity + sh.extra_equity
    eq_sem = np.zeros(NS)
    eq_sem[:4] = fin.equity * need_profile
    eq_sem[3] += sh.extra_equity

    # dette senior : tirages au prorata des besoins + tranche de réserve en S2-28
    draws = np.zeros(NS)
    draws[:4] = fin.debt * need_profile
    draws[3] += sh.standby_debt
    debt_amt = fin.debt + sh.standby_debt
    grace = fin.grace_sem + sh.extra_grace
    nrep = fin.n_repay_sem + sh.extra_tenor
    bal = 0.0
    d_int, d_prin, d_bal = np.zeros(NS), np.zeros(NS), np.zeros(NS)
    pay = None
    for s in range(NS):
        bal += draws[s]
        d_int[s] = bal * rs
        if s >= grace and bal > 1e-9:
            if pay is None:
                pay = _annuity(bal, rs, nrep) if fin.annuity else None
                lin = bal / nrep
            prin = (pay - d_int[s]) if fin.annuity else lin
            prin = min(prin, bal)
            d_prin[s] = prin
            bal -= prin
        d_bal[s] = bal
    fees = fin.arrangement_fee * debt_amt

    # crédit-bail : loyers semestriels à terme échu dès S2-28 (H61)
    l_rent, l_int, l_bal = np.zeros(NS), np.zeros(NS), np.zeros(NS)
    if lease_val > 0:
        lrs = (fin.lease_rate + sh.rate) / 2
        resid = fin.lease_residual * lease_val
        pv = lease_val - resid / (1 + lrs) ** fin.lease_sem
        rent = _annuity(pv, lrs, fin.lease_sem)
        lb = lease_val
        for i in range(fin.lease_sem):
            s = 3 + i
            if s >= NS:
                break
            l_int[s] = lb * lrs
            l_rent[s] = rent + (resid if i == fin.lease_sem - 1 else 0.0)
            lb = lb + l_int[s] - l_rent[s]
            l_bal[s] = max(lb, 0)
        l_bal[:3] = lease_val
        l_bal[2] = lease_val

    # prime à l'investissement + crédit relais
    prime = fin.prime_rate * ELIGIBLE_BASE * capex_mult * sh.prime_obtained if fin.prime_rate else 0.0
    prime_y = np.zeros(N)
    prime_y[2] = prime * 0.5
    prime_y[3] = prime * 0.5
    bridge = fin.bridge_share * fin.prime_rate * ELIGIBLE_BASE * capex_mult
    br_draw = np.zeros(N); br_draw[1] = bridge
    br_rep = np.zeros(N)
    br_bal = np.zeros(N)
    br_int = np.zeros(N)
    bb = 0.0
    for k in range(N):
        bb += br_draw[k]
        br_int[k] = bb * (r + fin.bridge_spread) * (0.5 if k == 1 else 1)
        rep = min(bb, prime_y[k]) if YEARS[k] < 2031 else (bb if YEARS[k] == 2031 else 0)
        br_rep[k] = rep
        bb -= rep
        br_bal[k] = bb

    agg = lambda x: x.reshape(N, 2).sum(1)
    end_y = lambda x: x.reshape(N, 2)[:, 1]
    interest = agg(d_int) + br_int
    principal = agg(d_prin)
    rents = agg(l_rent)
    lease_int = agg(l_int)
    debt_bal = end_y(d_bal)
    lease_bal = end_y(l_bal)
    eq_in = agg(eq_sem)
    debt_draw = agg(draws)

    # ---- Compte de résultat de la société de projet --------------------------
    # matériel en crédit-bail hors bilan : loyers en charges, pas d'amortissement
    lease_dep = np.zeros(N)
    if lease_val > 0:
        rem = lease_val
        for k in range(N):
            d = min(rem, lease_val * 0.10 * frac[k]); lease_dep[k] = d; rem -= d
    dep_co = dep - lease_dep
    ebitda_co = ebitda - rents
    prime_reco = np.zeros(N)
    if prime > 0:
        for k in range(N):
            prime_reco[k] = prime * 0.10 * frac[k] if YEARS[k] >= 2029 else 0
    fees_y = np.zeros(N); fees_y[0] = fees
    ebt = ebitda_co - dep_co - interest - fees_y + prime_reco
    tax = corporate_tax(ebt, fin.tax_holiday)
    net = ebt - tax

    # ---- Trésorerie et cascade des dividendes --------------------------------
    cash = np.zeros(N)
    div = np.zeros(N)
    cfads = np.zeros(N)
    service = np.zeros(N)
    dscr = np.full(N, np.nan)
    retained = 0.0
    c = 0.0
    min_cash = np.inf
    for k in range(N):
        cfads[k] = ebitda[k] - tax[k] - dbfr[k] - renew[k] - (capex_init[k] if YEARS[k] >= 2029 else 0)
        service[k] = interest[k] + principal[k] + rents[k]
        if service[k] > 1e-6 and YEARS[k] >= 2029:
            dscr[k] = cfads[k] / service[k]
        flow = (eq_in[k] + debt_draw[k] + br_draw[k] + prime_y[k]
                - (capex_init[k] - (lease_val if k == 1 else 0)) - renew[k]
                + ebitda[k] - tax[k] - dbfr[k] - interest[k] - principal[k] - rents[k]
                - br_rep[k] - fees_y[k])
        c += flow
        retained += net[k]
        if YEARS[k] >= 2030:
            ok = (np.isnan(dscr[k]) or dscr[k] >= DSCR_COVENANT)
            if ok and c > MIN_CASH and retained > 0:
                d = min(c - MIN_CASH, retained)
                div[k] = d
                c -= d
                retained -= d
        cash[k] = c
        min_cash = min(min_cash, c)

    net_debt = debt_bal + lease_bal + br_bal - cash
    lev = np.where(ebitda > 1, net_debt / np.maximum(ebitda, 1e-9), np.nan)

    # ---- Valorisation ---------------------------------------------------------
    test = (YEARS >= 2030)
    dscr_test = dscr[test & ~np.isnan(dscr)]
    dscr_min = float(np.nanmin(dscr_test)) if dscr_test.size else float("nan")
    dscr_avg = float(np.nanmean(dscr_test)) if dscr_test.size else float("nan")
    lev_max = float(np.nanmax(lev[test])) if np.any(test) else float("nan")

    avg_debt = float(np.mean((debt_bal + lease_bal)[1:]))
    E = equity_total
    D = avg_debt
    beta_l = mk.beta_u * (1 + (1 - mk.tax_shield) * D / E)
    ke = mk.rf + beta_l * mk.mrp + mk.specific_premium
    kd = ((debt_bal.mean() * r + lease_bal.mean() * (fin.lease_rate + sh.rate))
          / max(debt_bal.mean() + lease_bal.mean(), 1e-9))
    wacc = E / (E + D) * ke + D / (E + D) * kd * (1 - mk.tax_shield)

    fcff = ebitda - tax_u - dbfr - capex_total
    if fin.tax_holiday:
        fcff = fcff + (tax_u - tax_u_hol)
    fcff = fcff + prime_y - 0.35 * prime_reco
    gross_fa = capex_mult * CAPEX_BASE + renew.sum()
    nbv = gross_fa - dep.sum()
    if mk.tv_method == 1:
        tv = nbv + bfr[-1]
    elif mk.tv_method == 2:
        tv = fcff[-1] * (1 + mk.growth) / max(wacc - mk.growth, 1e-4)
    else:
        tv = mk.exit_multiple * ebitda[-1]
    fcff_tv = fcff.copy(); fcff_tv[-1] += tv
    disc = (1 + wacc) ** -(np.arange(N) + 1)
    npv = float(np.sum(fcff_tv * disc))
    tri = irr(np.concatenate([[0.0], fcff_tv]))

    eq_flows = -eq_in + div
    eq_tv = tv - debt_bal[-1] - lease_bal[-1] - br_bal[-1] + cash[-1]
    eq_flows_tv = eq_flows.copy(); eq_flows_tv[-1] += eq_tv
    tri_eq = irr(np.concatenate([[0.0], eq_flows_tv]))
    van_eq = float(np.sum(eq_flows_tv * (1 + ke) ** -(np.arange(N) + 1)))

    k32 = list(YEARS).index(2032)
    mcv_rate = (ca[k32] - var_costs[k32]) / ca[k32]
    breakeven = (fixed[k32] + dep_co[k32] + rents[k32] + interest[k32]) / mcv_rate

    funding_gap = max(0.0, -min_cash)
    dilution = max(0.0, (equity_total - EQUITY_CAPACITY) / equity_total)
    covenant_ok = (dscr_min >= DSCR_COVENANT) and (lev_max <= LEV_COVENANT) and min_cash >= 0

    table = {
        "Année": YEARS,
        "Volumes (kits)": vol,
        "Chiffre d'affaires": ca,
        "Charges variables": var_costs,
        "Charges fixes": fixed,
        "EBITDA économique": ebitda,
        "Marge EBITDA": np.where(ca > 0, ebitda / np.maximum(ca, 1e-9), 0),
        "Loyers crédit-bail": rents,
        "Dotations": dep_co,
        "Intérêts": interest,
        "Résultat avant impôt": ebt,
        "Impôt (IS)": tax,
        "Résultat net": net,
        "BFR": bfr,
        "Variation BFR": dbfr,
        "CAPEX": capex_total,
        "FCFF projet": fcff,
        "CFADS": cfads,
        "Service de la dette": service,
        "DSCR": dscr,
        "Dette bancaire (fin)": debt_bal,
        "Crédit-bail (encours)": lease_bal,
        "Crédit relais (fin)": br_bal,
        "Trésorerie (fin)": cash,
        "Dette nette retraitée": net_debt,
        "Levier DN/EBITDA": lev,
        "Apports FP": eq_in,
        "Dividendes": div,
        "Prime encaissée": prime_y,
    }
    return {
        "table": table,
        "kpi": {
            "Besoin de financement": float(capex_init.sum() + bfr[1] + 50 + fees + interest[:2].sum() * 0.0),
            "WACC": wacc,
            "Coût FP (Ke)": ke,
            "Bêta endetté": beta_l,
            "VAN projet": npv,
            "TRI projet": tri,
            "TRI FP": tri_eq,
            "VAN FP": van_eq,
            "DSCR min": dscr_min,
            "DSCR moyen": dscr_avg,
            "Levier max": lev_max,
            "Trésorerie min": float(min_cash),
            "Besoin non financé": funding_gap,
            "Dilution": dilution,
            "Valeur terminale": float(tv),
            "Point mort CA 2032": float(breakeven),
            "EBITDA 2032": float(ebitda[k32]),
            "CA 2032": float(ca[k32]),
            "Prime": prime,
            "Covenants OK": bool(covenant_ok),
        },
    }


# ---------------------------------------------------------------------------
# Analyses avancées
# ---------------------------------------------------------------------------
TORNADO_VARS = {
    "Prix de vente ±5 %": ("price", 0.05),
    "Volumes ±10 %": ("volume", 0.10),
    "Coût matières ±5 %": ("materials", 0.05),
    "Énergie ±20 %": ("energy", 0.20),
    "CAPEX ±15 %": ("capex_overrun", 0.15),
    "Retard ±6 mois": ("delay_months", 6),
    "Taux d'intérêt ±1 pt": ("rate", 0.01),
    "Délai clients ±15 j": ("dso_days", 15),
}


def tornado(fin: Financing, base: Shocks, mk: Market, metric="VAN projet"):
    ref = run(fin, base, mk)["kpi"][metric]
    out = []
    for label, (attr, delta) in TORNADO_VARS.items():
        b = getattr(base, attr)
        lo_v = max(0, b - delta) if attr == "delay_months" else b - delta
        lo = run(fin, replace(base, **{attr: lo_v}), mk)["kpi"][metric]
        hi = run(fin, replace(base, **{attr: b + delta}), mk)["kpi"][metric]
        out.append((label, lo - ref, hi - ref))
    out.sort(key=lambda x: max(abs(x[1]), abs(x[2])))
    return ref, out


MC_VARS = ["price", "volume", "materials", "energy", "capex_overrun", "delay_months", "rate"]
MC_DEFAULT_CORR = np.array([
    # prix  vol   mat   éner  capex retard taux
    [1.00, 0.30, 0.40, 0.20, 0.00, 0.00, 0.00],
    [0.30, 1.00, 0.00, 0.00, 0.00, -0.20, 0.00],
    [0.40, 0.00, 1.00, 0.50, 0.10, 0.00, 0.10],
    [0.20, 0.00, 0.50, 1.00, 0.10, 0.00, 0.10],
    [0.00, 0.00, 0.10, 0.10, 1.00, 0.60, 0.00],
    [0.00, -0.20, 0.00, 0.00, 0.60, 1.00, 0.00],
    [0.00, 0.00, 0.10, 0.10, 0.00, 0.00, 1.00],
])


def _norm_cdf(x):
    from math import erf, sqrt
    return 0.5 * (1 + np.vectorize(erf)(x / sqrt(2)))


def draw_mc(n: int, vol: dict, corr=MC_DEFAULT_CORR, seed: int | None = 42):
    """Tirages corrélés (copule gaussienne).

    vol : écarts-types {'price','volume','materials','energy','rate'}, CAPEX triangulaire
    (min, mode, max) et retard en mois (loi exponentielle tronquée de moyenne 'delay_mean').
    """
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(corr + 1e-9 * np.eye(len(corr)))
    z = rng.standard_normal((n, len(corr))) @ L.T
    u = _norm_cdf(z)
    s = {}
    s["price"] = z[:, 0] * vol["price"]
    s["volume"] = z[:, 1] * vol["volume"]
    s["materials"] = z[:, 2] * vol["materials"]
    s["energy"] = z[:, 3] * vol["energy"]
    a, m, b = vol["capex_tri"]
    uu = u[:, 4]
    fc = (m - a) / (b - a)
    s["capex_overrun"] = np.where(uu < fc, a + np.sqrt(uu * (b - a) * (m - a)),
                                  b - np.sqrt((1 - uu) * (b - a) * (b - m)))
    s["delay_months"] = np.minimum(-np.log(1 - np.clip(u[:, 5], 0, 0.9999)) * vol["delay_mean"], 18)
    s["rate"] = z[:, 6] * vol["rate"]
    return s


def monte_carlo(fin: Financing, base: Shocks, mk: Market, draws: dict, start=0, stop=None):
    n = len(draws["price"])
    stop = n if stop is None else min(stop, n)
    rows = []
    for i in range(start, stop):
        kw = {k: getattr(base, k) + float(draws[k][i]) for k in MC_VARS}
        kw["delay_months"] = max(0.0, kw["delay_months"])
        res = run(fin, replace(base, **kw), mk)["kpi"]
        rows.append({**{k: float(draws[k][i]) for k in MC_VARS},
                     "VAN projet": res["VAN projet"], "TRI projet": res["TRI projet"],
                     "TRI FP": res["TRI FP"], "DSCR min": res["DSCR min"],
                     "Levier max": res["Levier max"], "Trésorerie min": res["Trésorerie min"],
                     "Covenants OK": res["Covenants OK"]})
    return rows


def optimize(base: Shocks, mk: Market, equity_grid, lease_grid, need: float = 980.0,
             bank_cap: float = BANK_CAP, equity_cap: float = EQUITY_CAPACITY):
    """Recherche sur grille de la structure maximisant le TRI des FP sous contraintes."""
    out = []
    for e in equity_grid:
        for l in lease_grid:
            d = need - e - l
            if d < 0:
                continue
            f = Financing(f"E{e:.0f}/D{d:.0f}/L{l:.0f}", e, d, l,
                          lease_rate=0.065 if l > 0 else 0.0)
            k = run(f, base, mk)["kpi"]
            feasible = (d <= bank_cap and e <= equity_cap and k["Covenants OK"])
            out.append({"Fonds propres": e, "Dette": d, "Crédit-bail": l,
                        "TRI FP": k["TRI FP"], "VAN projet": k["VAN projet"],
                        "DSCR min": k["DSCR min"], "Levier max": k["Levier max"],
                        "Trésorerie min": k["Trésorerie min"], "WACC": k["WACC"],
                        "Admissible": feasible})
    return out


def scenario_to_dict(f: Financing) -> dict:
    return asdict(f)
