"""AMFI downloads: scheme master (with SEBI category) and daily NAV history."""
import io, re, time, datetime as dt
import numpy as np, pandas as pd, requests
from . import config as C

NAVALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
NAVALL_URLS = [NAVALL_URL, "https://www.amfiindia.com/spages/NAVAll.txt"]
HIST_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={f}&todt={t}"
CAT_RE = re.compile(r"^(Open[\s-]*Ended|Close[\s-]*Ended|Interval[\s-]*Funds?)\s*Schemes?\s*\((.+)\)\s*$", re.I)


def _kind(raw):
    r = raw.lower().replace("-", " ")
    return "Open Ended" if r.startswith("open") else "Close Ended" if r.startswith("close") else "Interval Fund"


def _get(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, headers=C.HTTP_HEADERS, timeout=120)
            r.raise_for_status()
            r.encoding = "utf-8"  # AMFI files are UTF-8; avoids garbled names like "Childrenâs"
            return r.text
        except Exception as e:  # network hiccups: back off and retry
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def _plan_option(name):
    n = " ".join(name.lower().split()).replace("dividend yield", "divyield")
    plan = "Direct" if "direct" in n else "Regular"
    if any(k in n for k in ("idcw", "dividend", "payout", "reinvest", "bonus", "income distribution")):
        opt = "IDCW/Other"
    elif "growth" in n or "gr " in n or n.endswith(" gr") or "cumulative" in n:
        opt = "Growth"
    else:
        opt = "Unknown"
    return plan, opt


def parse_navall(text):
    """NAVAll.txt -> one row per scheme with SEBI category taken from the section headers.
    Columns are located from the 'Scheme Code;...' header, so added/reordered columns are handled."""
    rows, cat, kind, amc = [], None, None, None
    col = dict(code=0, isin_g=1, isin_r=2, name=3, nav=4, date=-1, plan=None, option=None)
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = CAT_RE.match(s)
        if m:
            kind, cat = _kind(m.group(1)), m.group(2).strip()
            continue
        parts = [p.strip() for p in s.split(";")]
        low = [p.lower() for p in parts]
        if low[0].startswith("scheme code"):
            for j, h in enumerate(low):
                if "growth" in h and "isin" in h: col["isin_g"] = j
                elif "reinvest" in h and "isin" in h: col["isin_r"] = j
                elif h.startswith("scheme name"): col["name"] = j
                elif "net asset value" in h or h == "nav": col["nav"] = j
                elif h == "date" or h.endswith(" date"): col["date"] = j
                elif "plan" in h and "isin" not in h: col["plan"] = j
                elif "option" in h and "isin" not in h: col["option"] = j
            continue
        if len(parts) >= 6 and parts[0].isdigit():
            g = lambda k: parts[col[k]] if col[k] is not None and col[k] < len(parts) else ""
            name = g("name")
            label = " ".join(x for x in (name, g("plan"), g("option")) if x)
            plan, opt = _plan_option(label)
            isin_g, isin_r = g("isin_g"), g("isin_r")
            rows.append(dict(amfi_code=int(parts[0]), isin_growth=isin_g if isin_g not in ("-", "") else None,
                             isin_reinv=isin_r if isin_r not in ("-", "") else None, scheme_name=name,
                             amc=amc, scheme_type=kind, sebi_category=cat,
                             category_group=cat.split(" - ")[0].strip() if cat else None,
                             plan=plan, option=opt,
                             latest_nav=pd.to_numeric(g("nav").replace(",", ""), errors="coerce"),
                             nav_date=pd.to_datetime(g("date"), format="%d-%b-%Y", errors="coerce")))
        elif len(parts) == 1 and not low[0].startswith("scheme code"):
            amc = s  # AMC name lines sit between category header and schemes
    return pd.DataFrame(rows)


MFAPI_LIST = "https://api.mfapi.in/mf"


def _full_names():
    """Full scheme names (with plan/option) from mfapi.in's scheme list, keyed by AMFI code.
    AMFI's NAVAll.txt now shows only the base fund name, so plan/option is read from these."""
    try:
        r = requests.get(MFAPI_LIST, headers=C.HTTP_HEADERS, timeout=120)
        r.raise_for_status()
        return {int(x["schemeCode"]): x["schemeName"].strip() for x in r.json() if str(x.get("schemeCode", "")).isdigit()}
    except Exception as e:
        print(f"  WARNING: mfapi.in scheme list unavailable ({e}); plan/option from AMFI names only")
        return {}


def _looks_like_navall(text):
    head = text[:3000].lower()
    return "scheme code" in head and "<html" not in head


def scheme_master():
    """Download NAVAll.txt (tries each AMFI address) and keep open-ended schemes."""
    text, problems = None, []
    for url in NAVALL_URLS:
        try:
            t = _get(url)
        except Exception as e:
            problems.append(f"{url}: {e}")
            continue
        if _looks_like_navall(t):
            text = t
            break
        problems.append(f"{url}: unexpected content ({len(t):,} chars). Starts with: {t[:300]!r}")
    if text is None:
        raise RuntimeError("AMFI scheme master not usable (likely blocked or format changed):\n  "
                           + "\n  ".join(problems))
    df = parse_navall(text)
    if df.empty:
        raise RuntimeError("NAVAll.txt downloaded but no scheme rows parsed. First 500 chars:\n"
                           + repr(text[:500]))
    head = [l for l in text.splitlines() if l.strip()][:1]
    sample = next((l for l in text.splitlines() if l.split(";")[0].strip().isdigit()), "")
    print(f"  NAVAll header: {head[0][:250] if head else ''!r}")
    print(f"  NAVAll sample: {sample[:250]!r}")
    full = _full_names()
    if full:
        df["amfi_name"] = df["scheme_name"]
        df["scheme_name"] = [full.get(c, n) for c, n in zip(df.amfi_code, df.scheme_name)]
        po = [_plan_option(n) for n in df.scheme_name]
        df["plan"], df["option"] = [p for p, _ in po], [o for _, o in po]
    # When the name is silent: payout+reinvest ISIN pair => IDCW; single ISIN => Growth (flagged)
    df["option_source"] = "name"
    unk = (df.option == "Unknown")
    df.loc[unk & df.isin_reinv.notna(), ["option", "option_source"]] = ["IDCW/Other", "isin"]
    unk = (df.option == "Unknown")
    df.loc[unk & df.isin_growth.notna(), ["option", "option_source"]] = ["Growth", "isin"]
    print(f"  AMFI master: {len(df):,} rows; scheme types: {df.scheme_type.value_counts(dropna=False).to_dict()}")
    print(f"  plan: {df.plan.value_counts().to_dict()} | option: {df.option.value_counts().to_dict()}")
    mask = pd.Series(True, index=df.index)
    if getattr(C, "KEEP_TYPES", None):
        mask &= df.scheme_type.isin(C.KEEP_TYPES)
    if C.KEEP_GROUPS:
        mask &= df.category_group.isin(C.KEEP_GROUPS)
    keep = df[mask]
    if keep.empty:
        raise RuntimeError("No open-ended schemes in kept groups. Category groups seen: "
                           + str(df.category_group.value_counts().head(15).to_dict()))
    return keep.reset_index(drop=True)


HIST_URLS = [HIST_URL, "https://www.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={f}&todt={t}"]


def parse_history(text, keep_codes=None):
    """NAV history report -> (amfi_code, date, nav). Columns are found from the header line,
    so extra/reordered columns don't break it; falls back to the classic 8-column layout."""
    i_code, i_nav, i_date = 0, 4, 7
    out = []
    for line in text.splitlines():
        p = [x.strip() for x in line.split(";")]
        low = [x.lower() for x in p]
        if low and low[0].startswith("scheme code"):
            for j, h in enumerate(low):
                if h.startswith("scheme code"): i_code = j
                elif "net asset value" in h or h == "nav": i_nav = j
                elif h == "date" or h.startswith("nav date") or h.endswith(" date"): i_date = j
            continue
        if len(p) > max(i_code, i_nav, i_date) and p[i_code].isdigit():
            code = int(p[i_code])
            if keep_codes is not None and code not in keep_codes:
                continue
            out.append((code, p[i_nav], p[i_date]))
    if not out:
        return pd.DataFrame(columns=["amfi_code", "date", "nav"])
    df = pd.DataFrame(out, columns=["amfi_code", "nav", "date"])
    df["nav"] = pd.to_numeric(df["nav"].str.replace(",", ""), errors="coerce")
    d = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    if d.isna().mean() > 0.5:  # other date styles, e.g. 13-11-2026 or 2026-11-13
        d = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["date"] = d
    return df.dropna()[["amfi_code", "date", "nav"]]


def _fetch_hist(d, e, keep_codes, log):
    """One date window; tries each AMFI address. Logs what came back if nothing parses."""
    f, t = d.strftime("%d-%b-%Y"), e.strftime("%d-%b-%Y")
    notes = []
    for u in HIST_URLS:
        url = u.format(f=f, t=t)
        try:
            text = _get(url)
        except Exception as ex:
            notes.append(f"{url} -> error {ex}")
            continue
        part = parse_history(text, keep_codes)
        if len(part):
            return part
        all_rows = len(parse_history(text))
        notes.append(f"{url} -> {len(text):,} chars, {all_rows:,} rows before scheme filter; "
                     f"starts: {text[:400]!r}")
    for n in notes:
        log("    DIAG " + n)
    return pd.DataFrame(columns=["amfi_code", "date", "nav"])


MFAPI_URL = "https://api.mfapi.in/mf/{code}?startDate={s}&endDate={e}"
MFAPI_WORKERS = 8


def _mfapi_one(code, start, end):
    """Full NAV history for one scheme from mfapi.in (a mirror of AMFI's NAV data)."""
    url = MFAPI_URL.format(code=code, s=start.isoformat(), e=end.isoformat())
    for i in range(4):
        try:
            r = requests.get(url, headers=C.HTTP_HEADERS, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json().get("data") or []
            if not data:
                return None
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
            df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
            df = df.dropna()
            df = df[(df.date >= pd.Timestamp(start)) & (df.date <= pd.Timestamp(end)) & (df.nav > 0)]
            return df.assign(amfi_code=int(code))[["amfi_code", "date", "nav"]]
        except Exception:
            if i == 3:
                raise
            time.sleep(3 * (i + 1))


def nav_history(start, end, keep_codes, log=print):
    """Daily NAVs for the given schemes, via mfapi.in (AMFI's own history download now
    returns a web form instead of data, so it can't be automated)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    codes = sorted(keep_codes)
    log(f"  Fetching NAV history for {len(codes):,} schemes from mfapi.in …")
    frames, failed, empty = [], [], 0
    with ThreadPoolExecutor(MFAPI_WORKERS) as ex:
        futs = {ex.submit(_mfapi_one, c, start, end): c for c in codes}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                df = f.result()
                if df is None or not len(df):
                    empty += 1
                else:
                    frames.append(df)
            except Exception as e:
                failed.append(futs[f])
            if n % 500 == 0 or n == len(codes):
                log(f"    {n:,}/{len(codes):,} done | with data {len(frames):,} | empty {empty:,} | failed {len(failed):,}")
    if failed:
        log(f"  WARNING: {len(failed)} schemes failed to download, e.g. {failed[:10]}")
    if not frames:
        raise RuntimeError("mfapi.in returned no NAV data for any scheme.")
    out = pd.concat(frames, ignore_index=True)
    log(f"  NAV rows: {len(out):,} for {out.amfi_code.nunique():,} schemes")
    return out


# ================================================================================================
# Official AMFI website APIs (www.amfiindia.com/api/...): plan/option, NAV history, TER, SIF
# ================================================================================================
AMFI_API = "https://www.amfiindia.com/api"
SIF_CODE_BASE = 9_000_000          # SIF ids 'SIF-120' are stored as integer 9000120


def _api(path, tries=3, timeout=60):
    for i in range(tries):
        try:
            r = requests.get(AMFI_API + path, headers=C.HTTP_HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def latest_all_navs(kind="mf", log=print):
    """All schemes' NAV on the latest available date with official Plan / Option / ISINs.
    kind='mf' or 'sif'. Returns DataFrame (sd_id, nav_name, plan, option, isin_po, isin_ri, nav, nav_date, mf, scheme)."""
    path = "/nav-history" if kind == "mf" else "/sif-nav-history"
    d = dt.date.today()
    for back in range(0, 10):
        day = d - dt.timedelta(days=back)
        try:
            js = _api(f"{path}?query_type=all_for_date&from_date={day.isoformat()}")
        except Exception as e:
            log(f"  AMFI {kind} all_for_date {day}: {e}")
            continue
        rows = []
        for amc in js.get("data", []) or []:
            for sch in amc.get("schemes", []) or []:
                for n in sch.get("navs", []) or []:
                    rows.append({"sd_id": n.get("SD_ID"), "nav_name": n.get("NAV_Name"), "plan": n.get("Plan"),
                                 "option": n.get("Option"), "isin_po": n.get("ISIN_PO"), "isin_ri": n.get("ISIN_RI"),
                                 "nav": pd.to_numeric(n.get("hNAV_Amt"), errors="coerce"),
                                 "nav_date": str(n.get("hNAV_Date", ""))[:10], "mf": amc.get("mfName"),
                                 "scheme": sch.get("schemeName")})
        if rows:
            log(f"  AMFI {kind} latest NAVs: {len(rows):,} on {day}")
            return pd.DataFrame(rows)
    return pd.DataFrame()


def official_plan_option(master, log=print):
    """Overwrite plan / option with AMFI's own fields where available (more reliable than name parsing)."""
    try:
        off = latest_all_navs("mf", log)
    except Exception as e:
        log(f"  official plan/option unavailable: {e}")
        return master
    if off.empty:
        return master
    off = off[off.sd_id.astype(str).str.isdigit()].copy()
    off["amfi_code"] = off.sd_id.astype(int)
    pl = off.plan.fillna("").str.contains("Direct", case=False).map({True: "Direct", False: "Regular"})
    op = off.option.fillna("")
    opt = np.where(op.str.contains("growth|cumulative", case=False), "Growth",
                   np.where(op.str.contains("idcw|dividend|bonus|payout|reinvest", case=False), "IDCW/Other", None))
    off["plan_off"], off["option_off"] = pl.values, opt
    m = master.merge(off[["amfi_code", "plan_off", "option_off", "nav_name"]], on="amfi_code", how="left")
    has = m.plan_off.notna() & m.option_off.notna()
    m.loc[has, "plan"] = m.loc[has, "plan_off"]
    m.loc[has, "option"] = m.loc[has, "option_off"]
    m.loc[has, "option_source"] = "amfi"
    m.loc[m.nav_name.notna(), "scheme_name"] = m.loc[m.nav_name.notna(), "nav_name"]
    log(f"  plan/option from AMFI for {int(has.sum()):,} schemes")
    return m.drop(columns=["plan_off", "option_off", "nav_name"])


def amfi_history(sd_id, start, end, kind="mf"):
    """Official NAV history for one scheme (all its plan/option lines) -> (nav_name, date, nav)."""
    path = "/nav-history" if kind == "mf" else "/sif-nav-history"
    js = _api(f"{path}?query_type=historical_period&from_date={start}&to_date={end}&sd_id={sd_id}", timeout=120)
    rows = []
    for g in (js.get("data") or {}).get("nav_groups", []) or []:
        for r in g.get("historical_records", []) or []:
            rows.append((g.get("nav_name"), r.get("date"), r.get("nav")))
    return pd.DataFrame(rows, columns=["nav_name", "date", "nav"])


def nav_fallback(codes, start, end, log=print):
    """AMFI official history for schemes mfapi.in could not supply."""
    frames = []
    for c in codes:
        try:
            d = amfi_history(c, start, end)
        except Exception:
            continue
        if len(d):
            d = d.assign(amfi_code=int(c))
            frames.append(d)
    if not frames:
        return pd.DataFrame(columns=["amfi_code", "date", "nav"])
    out = pd.concat(frames)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["nav"] = pd.to_numeric(out["nav"], errors="coerce")
    log(f"  AMFI fallback NAVs: {out.amfi_code.nunique()} schemes")
    return out.dropna()[["amfi_code", "date", "nav"]]


# ------------------------------------------------------------------------------------------ SIF
SIF_STRATEGIES = [("Equity Ex-Top 100 Long-Short", r"ex.?top.?100"), ("Sector Rotation Long-Short", r"sector rotation"),
                  ("Sectoral Debt Long-Short", r"sectoral debt"), ("Debt Long-Short", r"debt"),
                  ("Active Asset Allocator Long-Short", r"asset allocator|active asset"),
                  ("Hybrid Long-Short", r"hybrid"), ("Equity Long-Short", r"equity")]


def sif_data(log=print):
    """SIF master + full NAV history from AMFI. Codes stored as 9,000,000 + numeric part of 'SIF-nnn'."""
    lat = latest_all_navs("sif", log)
    if lat.empty:
        return pd.DataFrame(), pd.DataFrame()
    lat["num"] = pd.to_numeric(lat.sd_id.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    lat = lat.dropna(subset=["num"])
    lat["amfi_code"] = (SIF_CODE_BASE + lat.num).astype(int)
    strat = []
    for n in lat.scheme.fillna(lat.nav_name):
        strat.append(next((s for s, rx in SIF_STRATEGIES if re.search(rx, str(n), re.I)), "Other SIF strategy"))
    master = pd.DataFrame({
        "amfi_code": lat.amfi_code, "scheme_name": lat.nav_name, "amfi_name": lat.scheme, "amc": lat.mf,
        "scheme_type": "SIF", "sebi_category": ["SIF - " + s for s in strat], "category_group": "SIF",
        "plan": np.where(lat.plan.fillna("").str.contains("Direct", case=False), "Direct", "Regular"),
        "option": np.where(lat.option.fillna("").str.contains("growth", case=False), "Growth", "IDCW/Other"),
        "isin_growth": lat.isin_po, "isin_reinv": lat.isin_ri.replace("", None), "latest_nav": lat.nav,
        "nav_date": pd.to_datetime(lat.nav_date, errors="coerce"), "option_source": "amfi"})
    frames = []
    start = "2025-01-01"
    for sd, g in lat.groupby("sd_id"):
        try:
            h = amfi_history(sd, start, dt.date.today().isoformat(), kind="sif")
        except Exception as e:
            log(f"  SIF {sd}: {e}")
            continue
        h = h.merge(g[["nav_name", "amfi_code"]], on="nav_name", how="inner")
        frames.append(h)
    navs = pd.concat(frames) if frames else pd.DataFrame(columns=["amfi_code", "date", "nav"])
    if len(navs):
        navs["date"] = pd.to_datetime(navs["date"])
        navs["nav"] = pd.to_numeric(navs["nav"], errors="coerce")
        navs = navs.dropna()[["amfi_code", "date", "nav"]]
    log(f"  SIF: {len(master):,} plan/option lines, NAV rows {len(navs):,}")
    return master, navs


# ------------------------------------------------------------------------------------------ TER
def ter_latest(log=print, page_size=100, workers=6):
    """Latest TER per scheme (Regular & Direct: total, base, brokerage, transaction, statutory) from AMFI.
    Uses the last complete month (falls back one more month if empty)."""
    from concurrent.futures import ThreadPoolExecutor
    today = dt.date.today().replace(day=1)
    for back in (0, 1, 2):
        m = (today - pd.DateOffset(months=back)).strftime("%m-%Y")
        base = f"/populate-te-rdata-revised?MF_ID=All&Month={m}&strCat=-1&strType=-1&pageSize={page_size}"
        try:
            first = _api(base + "&page=1")
        except Exception as e:
            log(f"  TER {m}: {e}")
            continue
        meta = first.get("meta") or {}
        pages = int(meta.get("pageCount") or 1)
        rows = list(first.get("data") or [])
        with ThreadPoolExecutor(workers) as ex:
            for js in ex.map(lambda p: _api(base + f"&page={p}"), range(2, pages + 1)):
                rows += js.get("data") or []
        if not rows:
            continue
        df = pd.DataFrame(rows)
        df["TER_Date"] = pd.to_datetime(df["TER_Date"], errors="coerce")
        df = df.sort_values("TER_Date").groupby("Scheme_Name", as_index=False).last()
        for c in [c for c in df.columns if c[:2] in ("R_", "D_")]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        log(f"  TER {m}: {len(df):,} schemes (from {len(rows):,} daily rows)")
        df.to_csv(C.OUT / "ter.csv", index=False)
        return df
    log("  TER: not available this run (keeping previous data/ter.csv if any)")
    f = C.OUT / "ter.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


def attach_ter(master, ter):
    """Adds ter_total, ter_base, ter_brokerage, ter_transaction, ter_statutory, ter_date by scheme & plan."""
    if ter is None or ter.empty:
        return master
    def k(x):
        return re.sub(r"[^a-z0-9]", "", str(x).lower())
    t = ter.copy()
    t["key"] = t.Scheme_Name.map(k)
    t = t.drop_duplicates("key").set_index("key")
    m = master.copy()
    base = m.get("amfi_name", m.scheme_name).fillna(m.scheme_name).map(k)
    for col, r_, d_ in [("ter_total", "R_TER", "D_TER"), ("ter_base", "R_BER", "D_BER"),
                        ("ter_brokerage", "R_BrokerageCost", "D_BrokerageCost"),
                        ("ter_transaction", "R_TransactionCost", "D_TransactionCost"),
                        ("ter_statutory", "R_StatutoryLevies", "D_StatutoryLevies")]:
        rv, dv = base.map(t[r_]) if r_ in t else np.nan, base.map(t[d_]) if d_ in t else np.nan
        m[col] = np.where(m.plan == "Direct", dv, rv)
    m["ter_date"] = base.map(t["TER_Date"]) if "TER_Date" in t else None
    return m
