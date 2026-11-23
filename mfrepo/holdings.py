"""AMC monthly portfolio disclosures -> stock/bond-level holdings -> portfolio characteristics.

Sources (config/amc_portfolio_sources.csv): one row per AMC with its disclosure page (from AMFI's
portfolio-disclosure listing). For each AMC the page is scanned for Excel/ZIP links; the latest month's
file(s) are downloaded and parsed. Any file placed in manual/portfolios/ (any AMC, any layout) is parsed
too — the fallback for AMCs whose website hides links behind scripts.

One generic parser handles every AMC layout: it finds each table by its header row (ISIN + % to NAV),
reads the scheme name from the rows above, tracks section headings (Equity / Debt / Money Market /
Derivatives / REIT / Others), and maps each scheme to AMFI codes by name.

Outputs
  data/holdings/holdings_<YYYY-MM>.parquet   one row per security per scheme
  data/holdings_summary.csv                  per scheme: allocation, market-cap split, YTM, credit mix...
  data/holdings_coverage.csv                 per AMC: downloaded? parsed? schemes matched
  data/mcap_classification.csv               AMFI large/mid/small list (ISIN -> bucket)
"""
from __future__ import annotations
import io, re, zipfile, difflib, datetime as dt
from pathlib import Path
from urllib.parse import urljoin
import numpy as np, pandas as pd, requests
from . import config as C

HDR = {**C.HTTP_HEADERS, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
FILE_RE = re.compile(r"""href\s*=\s*["']([^"']+?\.(?:xlsx|xlsm|xls|xlsb|zip|csv)(?:\?[^"']*)?)["']""", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], 1)}
RATING_ORDER = ["SOV", "AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
                "B", "C", "D", "Unrated", "TREPS/Cash"]


# ------------------------------------------------------------------------------------------ download
NOT_PORTFOLIO = r"overlap|top.?10|top.?ten|replication|dirf|riskometer|factsheet|fact.?sheet|\bter\b|expense|" \
                r"\bnav\b|debt.?index|fortnight|half.?year|semi.?annual|annual|scheme.?summary|sid|kim|addendum|" \
                r"notice|dividend|idcw|voting|stewardship|brokerage|commission|aum|riskometer"


def _month_score(text, target):
    """Score how well a link / file name matches the target month. -1 = wrong month or not a portfolio."""
    t = text.lower().replace("%20", " ")
    y, m = target.year, target.month
    mon = list(MONTHS)[m - 1]
    if re.search(NOT_PORTFOLIO, t):
        return -1
    years = set(re.findall(r"(?<!\d)(20\d{2})(?!\d)", t))
    has_mon = bool(re.search(rf"(?<![a-z]){mon}", t))
    num_mon = bool(re.search(rf"(?<!\d)(20\d{{2}}[-_./]?{m:02d}|{m:02d}[-_./]?20\d{{2}}|{m:02d}[-_./]?{y % 100:02d})(?!\d)", t))
    if years and str(y) not in years:
        return -1                                   # a different year is named
    if (has_mon or num_mon) and (str(y) in years or re.search(rf"{mon}[a-z]*[-_ ]?{y % 100:02d}(?!\d)", t)):
        score = 10
    elif has_mon or num_mon:
        score = 6
    elif not years:
        score = 1                                   # undated link: used only if nothing dated is found
    else:
        return -1
    other = [k for k in MONTHS if k != mon and re.search(rf"(?<![a-z]){k}(?![a-z])", t)]
    if other and not has_mon:
        return -1
    if re.search(r"portfolio|holding|monthly", t):
        score += 2
    return score


def find_links(page_url, target, session):
    r = session.get(page_url, headers=HDR, timeout=60)
    r.raise_for_status()
    links = {urljoin(page_url, h) for h in FILE_RE.findall(r.text)}
    scored = sorted(((_month_score(l, target), l) for l in links), reverse=True)
    dated = [l for s, l in scored if s >= 6]
    best = dated or [l for s, l in scored if s >= 1][:3]
    return best[:80], len(links)


def download_amc(row, target, session, outdir, log):
    res = {"amc": row.amc, "page": row.page_url, "links_found": 0, "files": 0, "status": ""}
    if not isinstance(row.page_url, str) or not row.page_url.startswith("http"):
        res["status"] = "no url"
        return res, []
    try:
        links, n = find_links(row.page_url, target, session)
        res["links_found"] = n
    except Exception as e:
        res["status"] = f"page error: {str(e)[:80]}"
        return res, []
    got = []
    for l in links:
        try:
            r = session.get(l, headers=HDR, timeout=120)
            r.raise_for_status()
            if len(r.content) < 2000:
                continue
            fn = outdir / re.sub(r"[^A-Za-z0-9._-]", "_", f"{row.amc[:30]}__{Path(l.split('?')[0]).name}")
            fn.write_bytes(r.content)
            got.append(fn)
        except Exception:
            continue
    res["files"] = len(got)
    res["status"] = "ok" if got else ("no matching file links (site may load links by script)" if n else
                                      "no file links on page (script-rendered site)")
    return res, got


# ------------------------------------------------------------------------------------------ parsing
def _read_any(path):
    """Yield (sheet_name, DataFrame without header) for xlsx/xls/xlsb/csv/zip."""
    p = Path(path)
    suf = p.suffix.lower()
    if suf == ".zip":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if re.search(r"\.(xlsx|xlsm|xls|xlsb|csv)$", n, re.I):
                    tmp = p.parent / f"_unz_{re.sub(r'[^A-Za-z0-9._-]', '_', Path(n).name)}"
                    tmp.write_bytes(z.read(n))
                    yield from _read_any(tmp)
        return
    if suf == ".csv":
        yield p.stem, pd.read_csv(p, header=None, dtype=str, encoding_errors="ignore")
        return
    engine = {".xls": "xlrd", ".xlsb": "pyxlsb"}.get(suf)
    try:
        sheets = pd.read_excel(p, sheet_name=None, header=None, dtype=str, engine=engine)
    except Exception:
        return
    for name, df in sheets.items():
        yield name, df


def _norm(x):
    return re.sub(r"\s+", " ", str(x)).strip() if pd.notna(x) else ""


def _num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).replace(",", "").replace("%", "").strip()
    s = re.sub(r"^\((.*)\)$", r"-\1", s)
    try:
        return float(s)
    except ValueError:
        return np.nan


COLS = {
    "name": r"name of (the )?(instrument|security|issuer)|instrument|security name|issuer|company|scrip|description",
    "isin": r"^isin|isin code|isin no",
    "industry": r"industry|sector|rating|classification",
    "rating": r"rating",
    "qty": r"quantity|qty|no\.? of (shares|units)|units",
    "mv": r"market.?value|market/fair value|fair value|value \(?rs|value in (rs|lakh|lacs|crore)|amount",
    "pct": r"%.*(nav|net asset|aum|net assets)|(nav|net assets?).*%|% to|% of|percentage|weight",
    "ytm": r"yield|ytm",
    "ytc": r"ytc|yield to call",
}
SECTIONS = [
    ("derivative", r"derivative|futures|options|short position|hedg"),
    ("equity", r"equity|shares|stock"),
    ("reit", r"reit|invit"),
    ("mf_units", r"mutual fund units|units of mutual|investment funds|fund of fund|etf units|foreign (mutual|fund)"),
    ("money_market", r"money market|certificate of deposit|commercial paper|treasury bill|t-?bill|cblo|treps|"
                     r"tri.?party|reverse repo|repo"),
    ("debt", r"debt|bond|debenture|ncd|government securit|g-?sec|state development|sdl|zero coupon|"
             r"securitised|pass through|ptc|non.?convertible|gilt"),
    ("gold", r"gold|silver|commodit"),
    ("cash", r"cash|net (current )?(assets|receivable)|margin|other current|receivable|payable"),
]


def _header_map(row):
    cells = [_norm(c).lower() for c in row]
    m = {}
    for i, c in enumerate(cells):
        if not c:
            continue
        for k, rx in COLS.items():
            if k not in m and re.search(rx, c):
                if k == "industry" and "rating" in c and "industry" not in c:
                    m.setdefault("rating", i)
                    continue
                m[k] = i
                break
    return m


def _is_header(row):
    m = _header_map(row)
    return "isin" in m and "pct" in m, m


def clean_title(t):
    t = re.sub(r"(?i)^\s*(name of (the )?scheme|scheme name|scheme)\s*[:\-]\s*", "", str(t))
    t = re.sub(r"\(.*?\)", " ", t)                                 # '(An open ended equity scheme ...)'
    t = re.sub(r"(?i)\b(monthly )?portfolio( statement)?( of)?\b", " ", t)
    t = re.sub(r"(?i)\s*(for|as on|as at)\s+(the month of\s+)?[a-z]*\s*\d{0,2}(st|nd|rd|th)?[\s,.\-]*\d{4}.*$", "", t)
    t = re.sub(r"(?i)\s*(for|as on)\s+\w+\s+\d{4}\s*$", "", t)
    return " ".join(t.split()).strip(" :-,")


def _scheme_title(df, upto):
    """Nearest line above a table that looks like a scheme name (not the AMC name or a date line)."""
    for i in range(upto - 1, max(-1, upto - 15), -1):
        txt = " ".join(_norm(c) for c in df.iloc[i].tolist() if _norm(c))
        if re.fullmatch(r"(?i)[\w\s&.\-]*mutual fund\W*", txt) or re.search(r"(?i)^\W*portfolio (statement )?as on", txt):
            continue
        if re.search(r"fund|scheme|plan|etf|fof|sif|portfolio of", txt, re.I) and len(txt) < 250 \
                and not re.search(r"name of (the )?instrument|isin", txt, re.I):
            txt = re.sub(r"(?i)(monthly )?portfolio( statement)?( of| as on| for)?.*?(?=[A-Z])", "", txt).strip()
            txt = re.sub(r"(?i)\s*(as on|as at|for the (month|period)).*$", "", txt).strip(" :-")
            txt = re.sub(r"(?i)^scheme name\s*[:\-]\s*", "", txt).strip()
            return txt
    return ""


def _rating_bucket(r):
    t = str(r).upper()
    if not t or t in ("NAN", "NONE"):
        return None
    if re.search(r"SOV|SOVEREIGN|GOI|GOVT|G-SEC|T-?BILL|TREASURY", t):
        return "SOV"
    t = t.replace("(CE)", "").replace("(SO)", "")
    if re.search(r"A1\+", t):
        return "AAA"
    if re.search(r"\bA1\b", t):
        return "AA"
    m = re.search(r"(?<![A-Z])(AAA|AA\+|AA-|AA|A\+|A-|BBB\+|BBB-|BBB|BB\+|BB-|BB|A|B|C|D)(?![A-Z0-9])", t)
    return m.group(1) if m else None


def parse_file(path, amc_hint=""):
    """Every holdings table in the file -> long DataFrame."""
    out = []
    for sheet, df in _read_any(path):
        df = df.dropna(how="all").reset_index(drop=True)
        if df.empty:
            continue
        i = 0
        while i < len(df):
            ok, hm = _is_header(df.iloc[i].tolist())
            if not ok:
                i += 1
                continue
            title = _scheme_title(df, i) or str(sheet)
            section = "equity"
            j = i + 1
            while j < len(df):
                row = df.iloc[j].tolist()
                ok2, _ = _is_header(row)
                if ok2:
                    break
                isin = _norm(row[hm["isin"]]) if hm.get("isin") is not None and hm["isin"] < len(row) else ""
                name = _norm(row[hm["name"]]) if hm.get("name") is not None and hm["name"] < len(row) else \
                    " ".join(_norm(c) for c in row[:2])
                pct = _num(row[hm["pct"]]) if hm["pct"] < len(row) else np.nan
                rowtxt = " ".join(_norm(c) for c in row if _norm(c)).lower()
                if re.search(r"grand total|net assets? \(|total net assets", rowtxt) and not isin:
                    if re.search(r"grand total", rowtxt):
                        j += 1
                        break
                if not isin and (np.isnan(pct) or re.search(r"^(total|sub ?total)", name.lower())):
                    for sec, rx in SECTIONS:  # a heading line switches the asset-class section
                        if re.search(rx, rowtxt) and not re.search(r"^(sub ?total|total)", rowtxt):
                            section = sec
                            break
                    j += 1
                    continue
                if np.isnan(pct) or (not isin and not name):
                    j += 1
                    continue
                rec = {"sheet": sheet, "scheme_title": title, "section": section, "name": name, "isin": isin,
                       "industry": _norm(row[hm["industry"]]) if hm.get("industry") is not None and hm["industry"] < len(row) else "",
                       "rating": _norm(row[hm["rating"]]) if hm.get("rating") is not None and hm["rating"] < len(row) else "",
                       "quantity": _num(row[hm["qty"]]) if hm.get("qty") is not None and hm["qty"] < len(row) else np.nan,
                       "market_value": _num(row[hm["mv"]]) if hm.get("mv") is not None and hm["mv"] < len(row) else np.nan,
                       "pct_nav": pct,
                       "ytm": _num(row[hm["ytm"]]) if hm.get("ytm") is not None and hm["ytm"] < len(row) else np.nan,
                       "ytc": _num(row[hm["ytc"]]) if hm.get("ytc") is not None and hm["ytc"] < len(row) else np.nan}
                # cash-like lines without ISIN
                if not isin and re.search(SECTIONS[-1][1], name.lower()):
                    rec["section"] = "cash"
                if not isin and re.search(r"treps|tri.?party|reverse repo|cblo", name.lower()):
                    rec["section"] = "money_market"
                out.append(rec)
                j += 1
            i = j
    df = pd.DataFrame(out)
    if df.empty:
        return df
    # % columns given as fractions (0.0523) -> percent
    df["scheme_title"] = df.scheme_title.map(clean_title)
    for t, g in df.groupby(["sheet", "scheme_title"]):
        if g.pct_nav.abs().max() <= 1.0 and g.pct_nav.clip(lower=0).sum() <= 2.5:
            df.loc[g.index, "pct_nav"] = g.pct_nav * 100
    # same scheme on several sheets of one file (e.g. repeated summary sheet): keep the fullest sheet
    n = df.groupby(["scheme_title", "sheet"]).size().rename("n").reset_index()
    keep = n.sort_values("n", ascending=False).drop_duplicates("scheme_title")[["scheme_title", "sheet"]]
    df = df.merge(keep, on=["scheme_title", "sheet"])
    df["amc_hint"] = amc_hint
    return df


def classify(df):
    """Final asset class per line, using section + ISIN pattern + rating."""
    def one(r):
        isin, sec, nm = str(r["isin"]).upper(), r["section"], str(r["name"]).lower()
        if sec == "derivative" or re.search(r"futures|\bfut\b|options|call option|put option", nm):
            return "derivative"
        m = re.match(r"^IN[E9]\w{4}(\d{2})\w{3}$", isin)
        if m:  # Indian corporate ISIN: security-type code after the issuer code
            t = m.group(1)
            if t in ("01", "02", "03"):
                return "equity"
            if t in ("14", "16"):          # commercial paper / certificate of deposit
                return "money_market"
            if re.search(r"reit|invit", nm):
                return "reit"
            return "money_market" if sec == "money_market" else "debt"
        if re.match(r"^IN\w{10}$", isin) and isin[:3] in ("IN0", "IN1", "IN2", "IN3", "IN4"):
            return "debt"  # G-Sec / SDL / T-Bill ISINs
        if re.match(r"^INF", isin):
            return "reit" if re.search(r"reit|invit|trust", nm) else "mf_units"
        if isin and not isin.startswith("IN"):
            return "foreign_equity" if sec in ("equity", "") else sec
        return sec
    df = df.copy()
    df["asset_class"] = df.apply(one, axis=1)
    df["rating_bucket"] = [(_rating_bucket(r) or _rating_bucket(i)) if ac in ("debt", "money_market") else None
                           for ac, r, i in zip(df.asset_class, df.rating, df.industry)]
    gsec = df["isin"].astype(str).str.match(r"^IN[0-4]") & df.asset_class.isin(["debt", "money_market"])
    df.loc[gsec, "rating_bucket"] = "SOV"
    treps = df["name"].astype(str).str.contains(r"(?i)treps|tri.?party|reverse repo|cblo|clearing corporation")
    df.loc[treps & df.asset_class.isin(["debt", "money_market"]), "rating_bucket"] = "TREPS/Cash"
    df.loc[df.asset_class.isin(["debt", "money_market"]) & df.rating_bucket.isna(), "rating_bucket"] = "Unrated"
    return df


# ------------------------------------------------------------------------------------------ matching
def _key(s):
    s = re.sub(r"(?i)\b(direct|regular|plan|growth|idcw|option|fund|scheme|the|an|open ended|ended|of|india|"
               r"mutual)\b", " ", str(s))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def match_schemes(titles, master, amc=None):
    """scheme_title -> AMFI base scheme (amfi_name) using token similarity within the AMC."""
    m = master.copy()
    strip = m.scheme_name.astype(str).str.replace(
        r"(?i)\s*[-–(]?\s*\b(direct|regular)\b.*$|\s*[-–]\s*(growth|idcw|dividend|bonus).*$", "", regex=True)
    m["base"] = m["amfi_name"].where(m["amfi_name"].notna(), strip) if "amfi_name" in m else strip
    cands = m
    if amc:
        a = _key(re.sub(r"(?i)mutual fund|asset management|amc|limited|ltd|company", "", amc)).split()[:2]
        if a:
            sel = m[m.amc.fillna("").str.lower().str.contains(a[0])]
            cands = sel if len(sel) else m
    bases = cands.drop_duplicates("base")
    keys = {b: _key(b) for b in bases.base}
    out = {}
    for t in titles:
        k = _key(t)
        if not k:
            continue
        best, score = None, 0
        for b, kb in keys.items():
            sc = difflib.SequenceMatcher(None, k, kb).ratio()
            tk, tb = set(k.split()), set(kb.split())
            sc = 0.5 * sc + 0.5 * (len(tk & tb) / max(len(tk | tb), 1))
            if sc > score:
                best, score = b, sc
        if best and score >= 0.62:
            out[t] = (best, round(score, 3))
    return out


# ------------------------------------------------------------------------------------------ market cap list
def mcap_list(log=print):
    """AMFI large/mid/small list. Tries config URLs, then manual/mcap/*.xlsx|csv."""
    frames = []
    today = dt.date.today()
    urls = list(getattr(C, "MCAP_URLS", []))
    for y in (today.year, today.year - 1):            # newest half-year list first
        for d in ("31Dec", "30Jun"):
            for base in ("https://portal.amfiindia.com/spages/", "https://www.amfiindia.com/Themes/Theme1/downloads/"):
                urls.append(f"{base}AverageMarketCapitalization{d}{y}.xlsx")
    for url in urls:
        try:
            r = requests.get(url, headers=HDR, timeout=60)
            r.raise_for_status()
            tmp = C.CACHE / "mcap_dl.xlsx"
            C.CACHE.mkdir(exist_ok=True)
            if len(r.content) < 20000:
                continue
            tmp.write_bytes(r.content)
            frames.append(tmp)
            log(f"  market-cap list: {url.rsplit('/', 1)[-1]}")
            break
        except Exception:
            continue
    frames += sorted((C.ROOT / "manual" / "mcap").glob("*.*")) if (C.ROOT / "manual" / "mcap").exists() else []
    rows = []
    for f in frames:
        for _, df in _read_any(f):
            df = df.dropna(how="all")
            for _, r in df.iterrows():
                vals = [_norm(v) for v in r.tolist()]
                isin = next((v for v in vals if re.fullmatch(r"INE\w{9}", v)), None)
                cat = next((v for v in vals if re.fullmatch(r"(?i)large ?cap|mid ?cap|small ?cap", v)), None)
                if isin and cat:
                    rows.append({"isin": isin, "mcap_bucket": re.sub(r"(?i)^(large|mid|small)\s*cap$",
                                                                    lambda m: m.group(1).title() + " Cap", cat)})
    df = pd.DataFrame(rows).drop_duplicates("isin")
    if len(df):
        df.to_csv(C.OUT / "mcap_classification.csv", index=False)
    elif (C.OUT / "mcap_classification.csv").exists():
        df = pd.read_csv(C.OUT / "mcap_classification.csv")
    log(f"  market-cap list: {len(df):,} ISINs")
    return df


# ------------------------------------------------------------------------------------------ summary
def summarise(h, mcap):
    """Per scheme: allocation, net equity, market-cap split, YTM, AAA+SOV %, rating mix, concentration."""
    if h.empty:
        return pd.DataFrame()
    h = h.copy()
    if len(mcap):
        h = h.merge(mcap, on="isin", how="left")
    else:
        h["mcap_bucket"] = np.nan
    rows = []
    for key, g in h.groupby(["amc", "scheme_title"]):
        p = g.pct_nav
        cls = g.asset_class
        eq_gross = p[cls.isin(["equity", "foreign_equity"])].sum()
        deriv = p[cls == "derivative"].sum()       # short futures are negative
        hedge = -deriv if deriv < 0 else 0.0
        debt_mask = cls.isin(["debt", "money_market"])
        debt = p[debt_mask].sum()
        d = g[debt_mask & g.pct_nav.notna()]
        ytm = float((d.ytm * d.pct_nav).sum() / d.pct_nav[d.ytm.notna()].sum()) if d.ytm.notna().any() and \
            d.pct_nav[d.ytm.notna()].sum() else np.nan
        rb_all = d.groupby("rating_bucket").pct_nav.sum()
        rb = rb_all.drop("TREPS/Cash", errors="ignore")
        rb_pct = (rb / rb.sum() * 100) if rb.sum() else rb
        rb_all_pct = (rb_all / rb_all.sum() * 100) if rb_all.sum() else rb_all
        mix = " · ".join(f"{k} {v:.0f}%" for k, v in sorted(rb_all_pct.items(), key=lambda kv: RATING_ORDER.index(kv[0])
                                                              if kv[0] in RATING_ORDER else 99) if v >= 0.5)
        eqs = g[cls == "equity"]
        mc = eqs.groupby(eqs.mcap_bucket.fillna("Unclassified")).pct_nav.sum()
        top10 = g[cls.isin(["equity", "foreign_equity"])].nlargest(10, "pct_nav").pct_nav.sum()
        rows.append({
            "amc": key[0], "scheme_title": key[1], "amfi_base": g.amfi_base.iloc[0] if "amfi_base" in g else None,
            "match_score": g.match_score.iloc[0] if "match_score" in g else None,
            "holdings_month": g.month.iloc[0] if "month" in g else None,
            "n_lines": len(g), "n_stocks": int((cls == "equity").sum()),
            "equity_gross_pct": eq_gross, "hedged_pct": hedge, "equity_net_pct": eq_gross - hedge,
            "foreign_equity_pct": p[cls == "foreign_equity"].sum(),
            "debt_pct": p[cls == "debt"].sum(), "money_market_pct": p[cls == "money_market"].sum(),
            "debt_total_pct": debt, "reit_invit_pct": p[cls == "reit"].sum(), "mf_units_pct": p[cls == "mf_units"].sum(),
            "gold_silver_pct": p[cls == "gold"].sum(), "cash_others_pct": p[cls == "cash"].sum(),
            "large_cap_pct": mc.get("Large Cap", 0.0), "mid_cap_pct": mc.get("Mid Cap", 0.0),
            "small_cap_pct": mc.get("Small Cap", 0.0), "mcap_unclassified_pct": mc.get("Unclassified", 0.0),
            "top10_equity_pct": top10, "ytm_pct": ytm,
            "aaa_sov_pct_of_debt": float(rb_pct.get("AAA", 0) + rb_pct.get("SOV", 0)) if len(rb_pct) else np.nan,
            "sov_pct_of_debt": float(rb_pct.get("SOV", 0)) if len(rb_pct) else np.nan,
            "below_aa_pct_of_debt": float(rb_pct[[k for k in rb_pct.index if k not in
                                                  ("SOV", "AAA", "AA+", "AA", "AA-", "Unrated")]].sum())
            if len(rb_pct) else np.nan,
            "credit_mix": mix, "total_pct": p.sum(),
        })
    return pd.DataFrame(rows)


def overlap(h, scheme_a, scheme_b, by="isin"):
    """Weight-based overlap (% of fund) between two schemes' equity holdings; net of hedged positions.
    scheme_a / scheme_b are amfi_base names (or scheme_title)."""
    def eq(s):
        g = h[(h.amfi_base == s) | (h.scheme_title == s)]
        g = g[g.asset_class.isin(["equity", "foreign_equity"])]
        return g.groupby(by).pct_nav.sum()
    a, b = eq(scheme_a), eq(scheme_b)
    common = a.index.intersection(b.index)
    return {"overlap_pct": float(np.minimum(a[common], b[common]).sum()), "common_stocks": len(common),
            "stocks_a": len(a), "stocks_b": len(b)}


# ------------------------------------------------------------------------------------------ pipeline
def run(master, log=print):
    cfg = C.CONFIG / "amc_portfolio_sources.csv"
    today = pd.Timestamp(dt.date.today())
    target = (today.replace(day=1) - pd.Timedelta(days=1))           # last completed month
    if today.day < 12:                                               # AMCs publish by ~10th
        target = target.replace(day=1) - pd.Timedelta(days=1)
    month = target.strftime("%Y-%m")
    dl = C.CACHE / "portfolios" / month
    dl.mkdir(parents=True, exist_ok=True)
    cov, files = [], []
    if cfg.exists():
        src = pd.read_csv(cfg)
        s = requests.Session()
        for r in src.itertuples():
            if str(getattr(r, "enabled", "Y")).upper().startswith("N"):
                continue
            res, got = download_amc(r, target, s, dl, log)
            cov.append(res)
            files += [(f, r.amc) for f in got]
            log(f"  {r.amc[:38]:38} links {res['links_found']:3}  files {res['files']:2}  {res['status']}")
    man = C.ROOT / "manual" / "portfolios"
    if man.exists():
        for f in sorted(man.rglob("*.*")):
            if f.suffix.lower() in (".xlsx", ".xlsm", ".xls", ".xlsb", ".zip", ".csv"):
                files.append((f, f.parent.name if f.parent != man else ""))
    frames = []
    for f, amc in files:
        try:
            d = parse_file(f, amc)
        except Exception as e:
            log(f"  parse failed {f.name}: {e}")
            continue
        if len(d):
            d["amc"] = amc or d.amc_hint
            d["source_file"] = f.name
            frames.append(d)
    if not frames:
        log("  holdings: no files parsed this run")
        pd.DataFrame(cov).to_csv(C.OUT / "holdings_coverage.csv", index=False)
        return
    h = classify(pd.concat(frames, ignore_index=True))
    h["month"] = month
    h["file_score"] = h.source_file.map(lambda f: _month_score(f, target))
    best = (h.groupby(["amc", "scheme_title", "source_file"]).file_score.first().reset_index()
            .sort_values("file_score", ascending=False).drop_duplicates(["amc", "scheme_title"]))
    h = h.merge(best[["amc", "scheme_title", "source_file"]], on=["amc", "scheme_title", "source_file"])
    h = h[h.file_score >= 0].drop(columns="file_score")
    h["amfi_base"], h["match_score"] = None, np.nan
    for amc, g in h.groupby("amc"):
        mp = match_schemes(g.scheme_title.unique(), master, amc)
        for t, (b, sc) in mp.items():
            sel = (h.amc == amc) & (h.scheme_title == t)
            h.loc[sel, "amfi_base"], h.loc[sel, "match_score"] = b, sc
    outdir = C.OUT / "holdings"
    outdir.mkdir(exist_ok=True)
    h.to_parquet(outdir / f"holdings_{month}.parquet", index=False)
    summ = summarise(h, mcap_list(log))
    summ.to_csv(C.OUT / "holdings_summary.csv", index=False)
    covdf = pd.DataFrame(cov)
    if len(covdf):
        parsed = h.groupby("amc").agg(schemes_parsed=("scheme_title", "nunique"),
                                      schemes_matched=("amfi_base", "nunique")).reset_index()
        covdf = covdf.merge(parsed, on="amc", how="left")
    covdf.to_csv(C.OUT / "holdings_coverage.csv", index=False)
    log(f"  holdings {month}: {h.scheme_title.nunique():,} scheme tables, {h.amfi_base.nunique():,} matched to AMFI, "
        f"{len(h):,} lines")
