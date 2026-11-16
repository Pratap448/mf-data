"""Refresh the repository: download AMFI + NSE Indices data, compute metrics, write data/*.csv.

Run:  python -m mfrepo.build            (full refresh / incremental if cache exists)
      python -m mfrepo.build --offline  (recompute metrics from cache only)
"""
import sys, json, re, datetime as dt
import numpy as np, pandas as pd
from . import config as C, amfi, indices, metrics as M, benchmarks as B, nse_prices

METRIC_COLS = ["ret_ytd", "ret_1y", "ret_3y", "ret_5y", "roll3y_avg", "sd_3y", "sharpe_3y", "beta_3y",
               "alpha_3y", "up_capture", "down_capture", "capture_ratio"]


def log(*a):
    print(*a, flush=True)


def load_cache(name):
    f = C.CACHE / f"{name}.parquet"
    return pd.read_parquet(f) if f.exists() else None


def save_cache(df, name):
    C.CACHE.mkdir(exist_ok=True)
    df.to_parquet(C.CACHE / f"{name}.parquet", index=False)


def bench_map(master):
    rules = pd.read_csv(C.CONFIG / "benchmark_map.csv")
    over = pd.read_csv(C.CONFIG / "scheme_benchmark_overrides.csv")
    over = dict(zip(over.amfi_code, over.benchmark_index)) if len(over) else {}

    def pick(row):
        if row.amfi_code in over:
            return over[row.amfi_code]
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


def refresh_tri(names, today):
    cache = load_cache("tri")
    have = set(cache["index"]) if cache is not None and len(cache) else set()
    full_start = pd.Timestamp(C.HISTORY_START).date()
    parts = []
    for n in names:
        if n in have and indices.manual(n) is None:
            last = cache[cache["index"] == n].date.max()
            parts.append(indices.tri_history([n], (last - pd.Timedelta(days=10)).date(), today.date(), log))
        else:
            parts.append(indices.tri_history([n], full_start, today.date(), log))
    tri = pd.concat([cache] + parts if cache is not None else parts, ignore_index=True)
    tri = tri.drop_duplicates(["index", "date"], keep="last").sort_values(["index", "date"])
    save_cache(tri, "tri")
    return tri


def main(offline=False):
    today = pd.Timestamp(dt.date.today())
    C.OUT.mkdir(exist_ok=True)
    if offline:
        master = pd.read_csv(C.OUT / "scheme_master.csv", parse_dates=["nav_date"])
        navs, tri = load_cache("navs"), load_cache("tri")
    else:
        log("Downloading AMFI scheme master…")
        master_all = amfi.scheme_master()
        master_all["benchmark_index"] = bench_map(master_all)
        master_all.to_csv(C.OUT / "scheme_master.csv", index=False)
        master = master_all
    full_master = master.copy()
    sib = sibling_map(full_master)
    # NAVs needed: every Growth option + any other option with no Growth sibling
    master = full_master[(full_master.option == "Growth") | (~full_master.amfi_code.isin(sib))].copy()
    log(f"Schemes: {len(full_master):,} total | {int((full_master.option == 'Growth').sum()):,} Growth | "
        f"{len(sib):,} IDCW/other mapped to Growth sibling | "
        f"{int(((full_master.option != 'Growth') & ~full_master.amfi_code.isin(sib)).sum()):,} without sibling (own NAV)")
    if not offline:
        navs = refresh_navs(master, today)
    if navs is None or not len(navs):
        raise RuntimeError("No NAV history available, so nothing to compute. Check the NAV/DIAG lines above.")
    asof = navs.date.max()
    if not offline:
        log("Building benchmark series…")
        tri, srcs = B.build(sorted(set(master.benchmark_index.dropna())), master, navs, asof, log)
        save_cache(tri, "tri")
        srcs.to_csv(C.OUT / "benchmark_sources.csv", index=False)
        try:
            log("Updating NSE equity index prices…")
            nse_prices.update(log)
        except Exception as e:  # price history is informational; never fail the run on it
            log(f"  WARNING: NSE index price update failed: {e}")
    log(f"As-of date: {asof.date()}  | schemes with NAVs: {navs.amfi_code.nunique():,}")

    tri_s = {n: g.set_index("date").tri.sort_index() for n, g in tri.groupby("index")} if len(tri) else {}
    bench_rows = []
    for n, s in tri_s.items():
        bench_rows.append({"benchmark_index": n, **{f"bm_{k}": v for k, v in M.period_returns(s, asof).items()},
                           "bm_roll3y_avg": M.rolling_avg(s, asof)})
    bench = pd.DataFrame(bench_rows)

    rows, series = [], {}
    for code, g in navs.groupby("amfi_code"):
        s = g.set_index("date").nav.sort_index()
        s = s[~s.index.duplicated(keep="last")]
        series[code] = s
        if s.index[-1] < asof - pd.Timedelta(days=10):
            continue  # stale / wound-up scheme
        rows.append({"amfi_code": code, "first_nav_date": s.index[0].date(), "last_nav_date": s.index[-1].date(),
                     **M.period_returns(s, asof), "roll3y_avg": M.rolling_avg(s, asof)})
    fm = master.merge(pd.DataFrame(rows), on="amfi_code", how="inner")

    risk = []
    for r in fm.itertuples():
        risk.append({"amfi_code": r.amfi_code, **M.risk_stats(series[r.amfi_code], tri_s.get(r.benchmark_index), asof)})
    fm = fm.merge(pd.DataFrame(risk), on="amfi_code", how="left")
    if len(bench):
        fm = fm.merge(bench, on="benchmark_index", how="left")
        for k in ["ytd", "1y", "3y", "5y"]:
            fm[f"excess_{k}"] = fm[f"ret_{k}"] - fm[f"bm_ret_{k}"]

    fm["peer_group"] = fm.apply(peer_key, axis=1)
    fm["metrics_basis"] = np.where(fm.option == "IDCW/Other",
                                   "own NAV (IDCW option, no Growth sibling: payouts not added back)", "own NAV")
    g = fm[fm.option == "Growth"]  # peers = Growth options only, so one fund isn't counted twice
    for col, tag in [("ret_3y", "3y"), ("roll3y_avg", "roll3y")]:
        rk = g.groupby("peer_group", group_keys=False)[col].apply(M.rank_quartile)
        rk.columns = [f"{c}_{tag}" for c in rk.columns]
        fm = fm.join(rk)

    cat = g.groupby("peer_group")[METRIC_COLS].mean().add_prefix("cat_avg_")
    cat["schemes"] = g.groupby("peer_group").size()
    cat = cat.reset_index()
    fm = fm.merge(cat.drop(columns="schemes"), on="peer_group", how="left")
    # IDCW / Bonus options: same fund & plan as a Growth option -> carry the Growth option's metrics
    sib_rows = full_master[full_master.amfi_code.isin(sib)].copy()
    if len(sib_rows):
        gm = fm.set_index("amfi_code")
        cols = [c for c in fm.columns if c not in full_master.columns]
        src = sib_rows.amfi_code.map(sib)
        ok = src.isin(gm.index)
        add = sib_rows[ok].reset_index(drop=True)
        vals = gm.loc[src[ok].values, cols].reset_index(drop=True)
        add = pd.concat([add, vals], axis=1)
        add["metrics_basis"] = "Growth option " + src[ok].astype(int).astype(str).values + " (same fund & plan)"
        fm = pd.concat([fm, add], ignore_index=True)
    fm.insert(0, "as_of", asof.date())

    num = fm.select_dtypes("number").columns.difference(["amfi_code", "latest_nav", "rank_3y", "count_3y",
                                                         "rank_roll3y", "count_roll3y", "quartile_3y", "quartile_roll3y"])
    fm[num] = fm[num].round(4)
    fm.to_csv(C.OUT / "fund_metrics.csv", index=False)
    cat.round(4).assign(as_of=asof.date()).to_csv(C.OUT / "category_stats.csv", index=False)

    if len(tri):
        tri[tri.date >= pd.Timestamp(C.HISTORY_START)].sort_values(["index", "date"]).round({"tri": 4}).to_csv(
            C.OUT / "benchmark_tri.csv.gz", index=False, compression="gzip")
        old = C.OUT / "benchmark_tri.csv"
        if old.exists():
            old.unlink()  # replaced by the .gz file
    me = navs.assign(m=navs.date.dt.to_period("M")).sort_values("date").groupby(["amfi_code", "m"]).last().reset_index()
    me[["amfi_code", "date", "nav"]].to_csv(C.OUT / "nav_month_end.csv.gz", index=False, compression="gzip")

    info = {"as_of": str(asof.date()), "run_at": dt.datetime.now().isoformat(timespec="seconds"),
            "schemes_in_master": int(len(full_master)), "schemes_with_metrics": int(len(fm)),
            "benchmarks_loaded": sorted(tri_s), "rf_rate": C.RF_RATE,
            "method": {"returns": "point-to-point NAV, CAGR for >1Y", "rolling": f"avg daily {C.ROLL_WINDOW_YEARS}Y CAGR, windows inside last {C.ROLL_DATA_YEARS}Y, needs {C.ROLL_DATA_YEARS}Y record",
                       "risk": f"{C.RISK_MONTHS} monthly returns; Sharpe vs RF; Jensen alpha & beta vs mapped TRI; capture = geometric up/down-month",
                       "peers": "SEBI category + plan (Regular/Direct), ranked on Growth options; IDCW/Bonus options carry their Growth sibling's metrics; close-ended/interval in own groups; index funds grouped by tracked index",
                       "category_avg": "simple average of peers"}}
    (C.OUT / "run_info.json").write_text(json.dumps(info, indent=1))
    log(json.dumps(info, indent=1))


if __name__ == "__main__":
    main(offline="--offline" in sys.argv)
