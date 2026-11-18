"""Refresh the repository: AMFI (master, NAV, TER, SIF), NSE (benchmarks), AMC portfolios -> data/.

Run:  python -m mfrepo.build            full refresh
      python -m mfrepo.build --offline  recompute every derived file from data/ only (no downloads)

The repo is a data store. Daily NAVs (data/nav/), benchmark and category index series let
mfrepo.analytics compute ANY measure for ANY period on demand; data/fund_metrics.* is a ready-made
snapshot of the standard measures (see data/COLUMNS.md).
"""
import sys, json, re, os, datetime as dt
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from . import config as C, amfi, indices, benchmarks as B, nse_prices, analytics as A


def log(*a):
    print(*a, flush=True)


def load_cache(name):
    f = C.CACHE / f"{name}.parquet"
    return pd.read_parquet(f) if f.exists() else None


def save_cache(df, name):
    C.CACHE.mkdir(exist_ok=True)
    df.to_parquet(C.CACHE / f"{name}.parquet", index=False)


_THEMES = None


def theme_of(row):
    """Sectoral/Thematic funds -> (theme label, [benchmark candidates in priority order])."""
    global _THEMES
    cat = str(row.sebi_category)
    if not re.search(r"sectoral|thematic", cat, re.I) or not re.search(r"equity", cat, re.I):
        return None, None
    if _THEMES is None:
        _THEMES = pd.read_csv(C.CONFIG / "theme_map.csv")
    name = str(row.scheme_name)
    brand = re.sub(r"\s*mutual fund\s*$", "", str(getattr(row, "amc", "") or ""), flags=re.I).strip()
    if brand and name.lower().startswith(brand.lower()):
        name = name[len(brand):]  # AMC brand words (e.g. 'Bajaj Finserv', 'Bank of India') are not the theme
    for t in _THEMES.itertuples():
        if re.search(t.pattern, name, re.I):
            return t.theme, t.benchmarks.split("|")
    return "Other theme", ["NIFTY 500"]


def bench_map(master):
    rules = pd.read_csv(C.CONFIG / "benchmark_map.csv")
    over = pd.read_csv(C.CONFIG / "scheme_benchmark_overrides.csv")
    over = dict(zip(over.amfi_code, over.benchmark_index)) if len(over) else {}

    def pick(row):
        if row.amfi_code in over:
            return over[row.amfi_code]
        th, cands = theme_of(row)
        if th:
            return "|".join(cands)  # resolved to the first candidate with data after benchmarks are built
        cat_txt = f"{row.sebi_category} {row.scheme_name}"
        if re.search(r"\bgold\b", cat_txt, re.I) and re.search(r"etf|fof|fund of fund", str(row.sebi_category), re.I) \
                and not re.search(r"silver", str(row.sebi_category), re.I):
            return "DOMESTIC GOLD PRICE"
        if re.search(r"\bsilver\b", cat_txt, re.I) and re.search(r"etf|fof|fund of fund", str(row.sebi_category), re.I):
            return "DOMESTIC SILVER PRICE"
        if re.search(r"index fund|etf", str(row.sebi_category), re.I):
            return B.tracked_index(row.scheme_name)  # index funds / ETFs: the index they track
        for t, b in zip(rules.match_text, rules.benchmark_index):
            if isinstance(row.sebi_category, str) and t.lower() in row.sebi_category.lower():
                return b
        return None
    return master.apply(pick, axis=1)


OPT_WORDS = re.compile(r"\s*[-–(]?\s*\b(direct|regular)\b.*$|\s*[-–]\s*(growth|idcw|dividend|bonus).*$", re.I)


def base_name(row):
    n = getattr(row, "amfi_name", None)
    if isinstance(n, str) and n.strip():
        return " ".join(n.lower().split())
    return " ".join(OPT_WORDS.sub("", str(row.scheme_name)).lower().split())


def sibling_map(master):
    """IDCW/Bonus/Unknown option -> Growth option of the same fund, same plan (same AMC, base name, category)."""
    m = master.copy()
    m["base_key"] = [base_name(r) for r in m.itertuples()]
    key = ["amc", "base_key", "sebi_category", "plan"]
    growth = m[m.option == "Growth"].drop_duplicates(key).set_index(key).amfi_code
    other = m[m.option != "Growth"]
    out = {}
    for r in other.itertuples():
        k = (r.amc, r.base_key, r.sebi_category, r.plan)
        if k in growth.index:
            out[r.amfi_code] = int(growth.loc[k])
    return out


def peer_key(row):
    """Peer group for ranking: SEBI category + plan; index funds/ETFs grouped by the index they track.
    Close-ended / interval schemes are kept in their own groups."""
    cat = row.sebi_category or ""
    th, _ = theme_of(row)
    if th:
        cat = f"{cat} | {th}"
    if getattr(row, "scheme_type", "Open Ended") not in ("Open Ended", None) and isinstance(row.scheme_type, str):
        cat = f"{row.scheme_type} | {cat}"
    if re.search(r"index fund|etf", cat, re.I):
        m = re.search(r"((nifty|sensex|bse|s&p|nasdaq|msci)[\w\s&\-]*?)(?=\s+(index|etf|fund|fof)\b)",
                      row.scheme_name, re.I)
        tracked = m.group(1).strip().upper() if m else "OTHER INDEX"
        return f"{cat} | {tracked} | {row.plan}"
    return f"{cat} | {row.plan}"


def refresh_navs(master, today):
    """Full history for every kept scheme on each run. mfapi.in is one request per scheme
    whatever the date range, so a partial refresh saves nothing and risks gaps."""
    keep = set(master.amfi_code)
    full_start = pd.Timestamp(C.HISTORY_START).date()
    log(f"NAV history (full, {len(keep):,} schemes) from {full_start} to {today.date()}")
    navs = amfi.nav_history(full_start, today.date(), keep, log)
    navs = navs.drop_duplicates(["amfi_code", "date"], keep="last")
    save_cache(navs, "navs")
    return navs




# ================================================================================================ NAV store
def norm_navs(navs):
    """One dtype contract for every NAV frame: amfi_code int64, date datetime64, nav float64."""
    if navs is None or len(navs) == 0:
        return pd.DataFrame({"amfi_code": pd.Series(dtype="int64"), "date": pd.Series(dtype="datetime64[ns]"),
                             "nav": pd.Series(dtype="float64")})
    n = navs[["amfi_code", "date", "nav"]].copy()
    n["amfi_code"] = pd.to_numeric(n["amfi_code"], errors="coerce")
    n["date"] = pd.to_datetime(n["date"], errors="coerce").astype("datetime64[ns]")
    n["nav"] = pd.to_numeric(n["nav"], errors="coerce").astype("float64")
    n = n.dropna()
    n["amfi_code"] = n["amfi_code"].astype("int64")
    return n[n.nav > 0].drop_duplicates(["amfi_code", "date"], keep="last").reset_index(drop=True)


def safe(step, status, fn, *a, default=None, **k):
    """Run an optional step; on failure log it, record it in run_info and continue."""
    try:
        out = fn(*a, **k)
        status[step] = "ok"
        return out
    except Exception as e:
        status[step] = f"failed: {type(e).__name__}: {str(e)[:200]}"
        log(f"  WARNING: {step} failed — {e}")
        return default


def nav_store_write(navs):
    """data/nav/nav_YYYY.parquet — one file per year; a year is rewritten only if its data changed."""
    d = C.OUT / "nav"
    d.mkdir(parents=True, exist_ok=True)
    navs = navs.copy()
    navs["amfi_code"] = navs["amfi_code"].astype("int64")
    navs["date"] = pd.to_datetime(navs["date"])
    navs["nav"] = navs["nav"].astype("float64").round(6)
    changed = 0
    for y, g in navs.groupby(navs["date"].dt.year):
        g = g.sort_values(["amfi_code", "date"]).reset_index(drop=True)
        f = d / f"nav_{y}.parquet"
        if f.exists():
            old = pd.read_parquet(f)
            old["date"] = pd.to_datetime(old["date"])
            if len(old) == len(g) and old.sort_values(["amfi_code", "date"]).reset_index(drop=True).equals(g):
                continue
        g.to_parquet(f, index=False, compression="zstd")
        changed += 1
    log(f"  NAV store: {navs.amfi_code.nunique():,} schemes, {len(navs):,} rows, {changed} year file(s) updated")


def nav_store_read():
    files = sorted((C.OUT / "nav").glob("nav_*.parquet"))
    if not files:
        return None
    n = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    n["date"] = pd.to_datetime(n["date"])
    return n


# ================================================================================================ category index
def category_index(master, series, asof):
    """Equal-weighted daily index of each peer group's Growth options (official-category average path).
    Daily moves beyond +/-20% are treated as data errors and ignored."""
    rows = []
    g = master[(master.option == "Growth") & master.amfi_code.isin(series.keys())]
    for pg, mem in g.groupby("peer_group"):
        rets = []
        for c in mem.amfi_code:
            s = series[c]
            r = s.pct_change()
            r = r[(r.abs() < 0.20)]
            rets.append(r.rename(c))
        if not rets:
            continue
        mat = pd.concat(rets, axis=1)
        avg = mat.mean(axis=1, skipna=True).dropna()
        cnt = mat.notna().sum(axis=1).reindex(avg.index)
        lvl = 1000 * (1 + avg).cumprod()
        rows.append(pd.DataFrame({"peer_group": pg, "date": lvl.index, "level": lvl.values, "members": cnt.values}))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["peer_group", "date", "level", "members"])
    out.to_parquet(C.OUT / "category_index.parquet", index=False, compression="zstd")
    log(f"  category index: {out.peer_group.nunique():,} peer groups")
    return {k: v.set_index("date").level for k, v in out.groupby("peer_group")}


# ================================================================================================ snapshot
_G = {}


def _snap(code):
    s = _G["series"].get(code)
    if s is None or len(s) < 2:
        return None
    asof, risk_end = _G["asof"], _G["risk_end"]
    if (asof - s.index[-1]).days > C.STALE_DAYS:
        return None
    meta = _G["meta"].get(code, {})
    bm = _G["bm"].get(meta.get("benchmark_index"))
    cat = _G["cat"].get(meta.get("peer_group"))
    out = {"amfi_code": code, "first_nav_date": s.index[0].date(), "last_nav_date": s.index[-1].date(),
           "last_nav": float(s.iloc[-1])}
    out.update(A.trailing_returns(s, asof))
    for y, v in A.calendar_returns(s, range(asof.year - C.CALENDAR_YEARS, asof.year)).items():
        out[f"cy_{y}"] = v
    for w in C.SNAPSHOT_WINDOWS:
        st = risk_end - pd.DateOffset(years=w)
        if not A.covers(s, st):
            continue
        sfx = f"_{w}y"
        rm = A.risk_measures(s, st, risk_end, C.RISK_FREQ)
        out.update({k + sfx: v for k, v in rm.items() if not k.startswith("dd_") or k in
                    ("dd_days_to_recover",)})
        if bm is not None and len(bm) and A.covers(bm, st):
            out.update({k + sfx: v for k, v in A.relative_measures(s, bm, st, risk_end, C.RISK_FREQ).items()})
        if cat is not None and len(cat) and A.covers(cat, st):
            out.update({k + sfx: v for k, v in
                        A.relative_measures(s, cat, st, risk_end, C.RISK_FREQ, prefix="cat_").items()})
    lb = asof - pd.DateOffset(years=C.ROLLING_LOOKBACK_YEARS)
    for w in C.ROLLING_WINDOWS:
        _, st = A.rolling_returns(s, w, lb, asof, "W", bm if bm is not None and len(bm) else None)
        out.update({f"{k}_{w.lower()}": v for k, v in st.items()})
    return out


RANK_COLS_BASE = ["ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y", "ret_2y", "ret_3y", "ret_5y", "ret_7y", "ret_10y"]
RANK_COLS_WIN = ["ann_return", "std_dev", "downside_dev", "sharpe", "sortino", "calmar", "max_drawdown", "alpha",
                 "information_ratio", "capture_ratio", "up_capture", "down_capture", "batting_avg", "excess_return"]


def snapshot(master, series, bm, cat, asof):
    risk_end = (asof + pd.offsets.MonthEnd(0)) if asof.is_month_end else (asof - pd.offsets.MonthEnd(1))
    meta = master.set_index("amfi_code")[["benchmark_index", "peer_group"]].to_dict("index")
    codes = [c for c in master.amfi_code if c in series]
    _G.update(series=series, bm=bm, cat=cat, meta=meta, asof=asof, risk_end=risk_end)
    workers = max(1, min(4, (os.cpu_count() or 2)))
    rows = []
    try:
        with ProcessPoolExecutor(workers) as ex:
            for r in ex.map(_snap, codes, chunksize=50):
                if r:
                    rows.append(r)
    except Exception as e:   # no fork available -> single process
        log(f"  parallel snapshot unavailable ({e}); running single-process")
        rows = [r for r in map(_snap, codes) if r]
    fm = pd.DataFrame(rows)
    log(f"  snapshot: {len(fm):,} schemes, {fm.shape[1]:,} columns, risk window end {risk_end.date()}")
    return fm, risk_end


def bench_trailing(bm, asof):
    rows = []
    for n, s in bm.items():
        d = {"benchmark_index": n}
        d.update({f"bm_{k}": v for k, v in A.trailing_returns(s, asof).items()})
        rows.append(d)
    return pd.DataFrame(rows)


def cat_trailing(cat, asof):
    rows = []
    for n, s in cat.items():
        d = {"peer_group": n}
        d.update({f"catidx_{k}": v for k, v in A.trailing_returns(s, asof).items()})
        rows.append(d)
    return pd.DataFrame(rows)


# ================================================================================================ main
def write_columns_doc(fm):
    lines = ["# fund_metrics columns", "",
             "Suffix `_Ny` = measured over the last N years to the last month-end (monthly returns unless config says otherwise).",
             "Prefix `cat_` = measured against the category-average index instead of the benchmark.",
             "`_rank/_of/_pctile/_quartile` = position within the peer group (Growth options only; 1 = best).",
             "", "| column | meaning |", "|---|---|"]
    desc = {"ret_": "trailing point-to-point return %, CAGR above 1 year", "cy_": "calendar-year return %",
            "ann_return": "annualised return %", "std_dev": "annualised standard deviation %",
            "downside_dev": "annualised downside deviation % (below risk-free)", "sharpe": "Sharpe ratio",
            "sortino": "Sortino ratio", "calmar": "annualised return / max drawdown", "max_drawdown": "max drawdown % (daily)",
            "ulcer_index": "Ulcer index", "longest_underwater_days": "longest period below a previous peak (days)",
            "current_drawdown": "drawdown from peak at window end %", "var_95": "95% value-at-risk per period %",
            "cvar_95": "95% expected shortfall per period %", "omega": "Omega ratio", "skewness": "skewness",
            "kurtosis": "excess kurtosis", "beta": "beta", "alpha": "Jensen's alpha % p.a.", "r_squared": "R-squared %",
            "correlation": "correlation", "tracking_error": "tracking error % p.a.", "information_ratio": "information ratio",
            "treynor": "Treynor ratio %", "m2": "Modigliani M-squared %", "up_capture": "up-market capture % (geometric)",
            "down_capture": "down-market capture % (geometric)", "capture_ratio": "up capture / down capture",
            "batting_avg": "% of periods beating the benchmark", "excess_return": "annualised return minus benchmark's",
            "active_return": "same as excess_return", "roll_": "rolling-return statistics over the last 10 years",
            "bm_": "benchmark value of the same measure", "catidx_": "category-average index trailing return",
            "cat_avg_": "simple average of peers", "cat_median_": "median of peers", "ter_": "expense ratio %"}
    for c in fm.columns:
        d = next((v for k, v in desc.items() if c.startswith(k) or c.replace("cat_", "", 1).startswith(k)), "")
        lines.append(f"| {c} | {d} |")
    (C.OUT / "COLUMNS.md").write_text("\n".join(lines))


def main(offline=False):
    today = pd.Timestamp(dt.date.today())
    C.OUT.mkdir(exist_ok=True)
    C.CACHE.mkdir(exist_ok=True)
    status = {}

    # ---------- master
    if offline:
        master_all = pd.read_csv(C.OUT / "scheme_master.csv", low_memory=False)
    else:
        log("Downloading AMFI scheme master…")
        master_all = amfi.scheme_master()
        master_all = safe("official_plan_option", status, amfi.official_plan_option, master_all, log,
                          default=master_all)
        sif_m, sif_n = pd.DataFrame(), pd.DataFrame()
        if C.INCLUDE_SIF:
            sif_m, sif_n = safe("sif", status, amfi.sif_data, log, default=(pd.DataFrame(), pd.DataFrame()))
            if len(sif_m):
                master_all = pd.concat([master_all, sif_m], ignore_index=True)
    master_all["benchmark_index"] = bench_map(master_all)
    master_all["peer_group"] = master_all.apply(peer_key, axis=1)
    sib = sibling_map(master_all)
    master_all["nav_source_code"] = master_all.amfi_code.map(sib).fillna(master_all.amfi_code).astype("int64")
    need = master_all[(master_all.option == "Growth") | (~master_all.amfi_code.isin(sib))]
    log(f"Schemes: {len(master_all):,} | NAV histories needed: {len(need):,} (others use their Growth sibling)")

    # ---------- NAVs
    if offline:
        navs = norm_navs(nav_store_read())
    else:
        mf = need[need.amfi_code < amfi.SIF_CODE_BASE]
        navs = norm_navs(refresh_navs(mf, today))
        got = set(navs.amfi_code.unique())
        missing = [c for c in mf.amfi_code if c not in got]
        if missing:
            fb = safe("nav_fallback", status, amfi.nav_fallback, missing[:400], C.HISTORY_START,
                      today.date().isoformat(), log, default=None)
            navs = norm_navs(pd.concat([navs, norm_navs(fb)], ignore_index=True))
        if len(sif_n):
            navs = norm_navs(pd.concat([navs, norm_navs(sif_n)], ignore_index=True))
        nav_store_write(navs)
    if navs is None or not len(navs):
        raise RuntimeError("No NAV history available.")
    asof = navs.date.max()
    series = {c: A.clean(pd.Series(g.nav.to_numpy(), index=g.date.to_numpy())) for c, g in navs.groupby("amfi_code")}
    log(f"As-of {asof.date()} | schemes with NAVs {len(series):,}")

    # ---------- benchmarks
    prev_tri = C.OUT / "benchmark_tri.csv.gz"
    tri = None
    if not offline:
        log("Building benchmark series…")
        names = sorted({n for v in need.benchmark_index.dropna() for n in str(v).split("|")} | {"NIFTY 50", "NIFTY 500"})
        res = safe("benchmarks", status, B.build, names, need, navs, asof, log, default=None)
        if res is not None:
            tri, srcs = res
            tri["date"] = pd.to_datetime(tri["date"]).astype("datetime64[ns]")
            srcs.to_csv(C.OUT / "benchmark_sources.csv", index=False)
            tri[tri.date >= pd.Timestamp(C.HISTORY_START)].sort_values(["index", "date"]).round({"tri": 4}).to_csv(
                prev_tri, index=False, compression="gzip")
        safe("nse_prices", status, nse_prices.update, log)
    if tri is None:
        tri = pd.read_csv(prev_tri, parse_dates=["date"]) if prev_tri.exists() else \
            pd.DataFrame(columns=["index", "date", "tri"])
    bm = {n: A.clean(g.set_index("date").tri) for n, g in tri.groupby("index")}

    def resolve(v):
        if not isinstance(v, str) or "|" not in v:
            return v
        c = v.split("|")
        return next((x for x in c if x in bm), c[0])
    master_all["benchmark_index"] = master_all.benchmark_index.map(resolve)

    # ---------- category index
    cat = safe("category_index", status, category_index, master_all[master_all.amfi_code.isin(series.keys())],
               series, asof, default={})

    # ---------- TER
    ter = None
    if not offline and C.FETCH_TER:
        ter = safe("ter", status, amfi.ter_latest, log, default=None)
    if ter is None or not len(ter):
        f = C.OUT / "ter.csv"
        ter = pd.read_csv(f) if f.exists() else pd.DataFrame()
    master_all = safe("attach_ter", status, amfi.attach_ter, master_all, ter, default=master_all)
    master_all.to_csv(C.OUT / "scheme_master.csv", index=False)

    # ---------- snapshot of standard measures
    calc = master_all[master_all.amfi_code.isin(series.keys())]
    fm, risk_end = snapshot(calc, series, bm, cat, asof)
    base_cols = ["amfi_code", "scheme_name", "amc", "scheme_type", "sebi_category", "category_group", "plan", "option",
                 "peer_group", "benchmark_index", "isin_growth", "isin_reinv"] + \
                [c for c in master_all.columns if c.startswith("ter_")]
    fm = master_all[[c for c in base_cols if c in master_all.columns]].merge(fm, on="amfi_code", how="inner")
    fm["metrics_basis"] = np.where(fm.option == "IDCW/Other",
                                   "own NAV (IDCW option, no Growth sibling: payouts not added back)", "own NAV")
    # IDCW / Bonus options take their Growth sibling's measures
    sibs = master_all[master_all.amfi_code.isin(sib.keys())]
    if len(sibs):
        src = fm.set_index("amfi_code")
        mcols = [c for c in fm.columns if c not in base_cols]
        add = sibs[[c for c in base_cols if c in sibs.columns]].copy()
        add["src"] = add.amfi_code.map(sib)
        add = add[add.src.isin(src.index)]
        vals = src.loc[add.src, mcols].reset_index(drop=True)
        add = pd.concat([add.reset_index(drop=True), vals], axis=1)
        add["metrics_basis"] = "Growth option " + add.src.astype(str) + " (same fund & plan)"
        fm = pd.concat([fm, add.drop(columns="src")], ignore_index=True)
    fm = fm.merge(bench_trailing(bm, asof), on="benchmark_index", how="left")
    fm = fm.merge(cat_trailing(cat, asof), on="peer_group", how="left")

    # ---------- peer ranks and category stats (Growth options only)
    g = fm[(fm.option == "Growth") & (fm.metrics_basis == "own NAV")]
    rank_cols = [c for c in RANK_COLS_BASE if c in fm] + \
                [f"{m}_{w}y" for w in C.SNAPSHOT_WINDOWS for m in RANK_COLS_WIN if f"{m}_{w}y" in fm] + \
                [f"roll_avg_{w.lower()}" for w in C.ROLLING_WINDOWS if f"roll_avg_{w.lower()}" in fm]
    ranked = A.rank_table(g[["amfi_code", "peer_group"] + rank_cols], rank_cols, "peer_group", C.MIN_PEERS)
    rcols = [c for c in ranked.columns if c.endswith(("_rank", "_of", "_pctile", "_quartile"))]
    rk = ranked.set_index("amfi_code")[rcols]
    src_code = fm.amfi_code.where(fm.metrics_basis.str.startswith("own NAV"),
                                  fm.metrics_basis.str.extract(r"Growth option (\d+)")[0].astype(float))
    fm = pd.concat([fm.reset_index(drop=True), rk.reindex(src_code.astype("Int64")).reset_index(drop=True)], axis=1)
    num = [c for c in g.columns if c not in base_cols and pd.api.types.is_numeric_dtype(g[c])
           and not c.startswith(("bm_", "catidx_")) and c not in ("last_nav",)]
    stats = pd.concat([g.groupby("peer_group")[num].mean().add_prefix("cat_avg_"),
                       g.groupby("peer_group")[num].median().add_prefix("cat_median_"),
                       g.groupby("peer_group").size().rename("peers")], axis=1).reset_index()
    stats.round(4).to_parquet(C.OUT / "category_stats.parquet", index=False, compression="zstd")
    key_stats = ["peer_group", "peers"] + [f"cat_avg_{c}" for c in rank_cols if f"cat_avg_{c}" in stats]
    stats[key_stats].round(4).to_csv(C.OUT / "category_stats.csv", index=False)
    fm = fm.merge(stats[key_stats], on="peer_group", how="left")
    fm.insert(0, "as_of", asof.date())
    fm["risk_window_end"] = risk_end.date()
    num_all = fm.select_dtypes("number").columns.difference(["amfi_code", "last_nav"])
    fm[num_all] = fm[num_all].astype("float64").round(4)
    fm.to_parquet(C.OUT / "fund_metrics.parquet", index=False, compression="zstd")
    fm.to_csv(C.OUT / "fund_metrics.csv.gz", index=False, compression="gzip")
    old_csv = C.OUT / "fund_metrics.csv"
    if old_csv.exists():
        old_csv.unlink()
    write_columns_doc(fm)
    me = navs.assign(m=navs.date.dt.to_period("M")).sort_values("date").groupby(["amfi_code", "m"]).last().reset_index()
    me[["amfi_code", "date", "nav"]].to_csv(C.OUT / "nav_month_end.csv.gz", index=False, compression="gzip")

    # ---------- holdings
    if not offline and C.FETCH_HOLDINGS:
        from . import holdings
        log("AMC portfolios…")
        safe("holdings", status, holdings.run, master_all, log)

    info = {"as_of": str(asof.date()), "risk_window_end": str(risk_end.date()),
            "run_at": dt.datetime.now().isoformat(timespec="seconds"),
            "schemes_in_master": int(len(master_all)), "schemes_with_metrics": int(len(fm)),
            "nav_histories": len(series), "benchmarks_loaded": len(bm), "category_indices": len(cat),
            "rf_rate": C.RF_RATE, "risk_freq": C.RISK_FREQ, "status": status,
            "files": sorted(p.name for p in C.OUT.glob("*") if p.is_file())}
    (C.OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=str))
    log(json.dumps(info, indent=1, default=str))


if __name__ == "__main__":
    main(offline="--offline" in sys.argv)
