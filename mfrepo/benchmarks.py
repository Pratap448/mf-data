"""Benchmark index series built from index-tracking schemes (index funds / ETFs).

For each benchmark index the longest-running Direct index fund (or ETF) that tracks it exactly is
chosen; its daily NAV is grossed up for an assumed annual expense (config.BENCH_ER_ADDBACK) to
approximate the index's total-return series. A hand-placed CSV in manual/tri/<INDEX>.csv
(columns Date,TRI) always takes priority. Source scheme per index is written to
data/benchmark_sources.csv for audit.
"""
import re
import numpy as np, pandas as pd
from . import config as C, indices

TRACK_RE = re.compile(r"((nifty|sensex|bse|s&p|nasdaq|msci|crisil)[\w\s&\-:]*?)(?=\s+(index|etf|fund|fof)\b)", re.I)


def norm(name):
    return re.sub(r"[^A-Z0-9&:]", "", str(name).upper())


def tracked_index(scheme_name):
    m = TRACK_RE.search(str(scheme_name))
    return m.group(1).strip().upper() if m else None


def candidates(master):
    """Index funds / ETFs with the index they track (normalised key)."""
    m = master[master.sebi_category.fillna("").str.contains("Index Fund|ETF", case=False, regex=True)].copy()
    m = m[m.option != "IDCW/Other"]
    m["track"] = m.scheme_name.map(tracked_index)
    m["track_key"] = m.track.map(lambda x: norm(x) if x else None)
    return m.dropna(subset=["track_key"])


_OFFICIAL = None


def official():
    """Official NSE TRI history (manual/official_tri.csv: index,date,tri), keyed by normalised name."""
    global _OFFICIAL
    if _OFFICIAL is None:
        _OFFICIAL = {}
        for f in [C.ROOT / "manual" / "official_tri.csv", C.ROOT / "manual" / "official_debt.csv",
                  C.ROOT / "manual" / "official_extra.csv"]:
            if not f.exists():
                continue
            d = pd.read_csv(f)
            d["date"] = pd.to_datetime(d["date"], format="mixed", dayfirst=True, errors="coerce")
            d["tri"] = pd.to_numeric(d["tri"], errors="coerce")
            for n, g in d.dropna().groupby("index"):
                g = g.drop_duplicates("date", keep="last")
                _OFFICIAL[norm(n)] = g.set_index("date").tri.sort_index()
    return _OFFICIAL


_PRICES = None


def price_series(name):
    """NSE price index (data/index_price.csv.gz) for short top-ups of official TRI history."""
    global _PRICES
    if _PRICES is None:
        f = C.OUT / "index_price.csv.gz"
        _PRICES = {}
        if f.exists():
            d = pd.read_csv(f, parse_dates=["date"])
            for n, g in d.groupby("index"):
                _PRICES[norm(n)] = g.set_index("date").close.sort_index()
    return _PRICES.get(norm(name))


# Indices whose NSE daily-file level already includes all returns (strategy / G-Sec total-return indices)
LEVEL_IS_TR = {norm(x) for x in ["NIFTY 50 ARBITRAGE", "NIFTY COMPOSITE G-SEC INDEX", "NIFTY 4-8 YR G-SEC INDEX",
                                 "NIFTY 8-13 YR G-SEC", "NIFTY 11-15 YR G-SEC INDEX", "NIFTY 15 YR AND ABOVE G-SEC INDEX",
                                 "NIFTY 1D RATE INDEX", "NIFTY BHARAT BOND INDEX - APRIL 2030",
                                 "NIFTY BHARAT BOND INDEX - APRIL 2031", "NIFTY BHARAT BOND INDEX - APRIL 2032",
                                 "NIFTY BHARAT BOND INDEX - APRIL 2033"]}

COMMODITY = {"DOMESTIC GOLD PRICE": "gold", "DOMESTIC SILVER PRICE": "silver"}


def commodity_candidates(master, metal):
    """Gold / Silver ETFs only (FoFs and multi-asset excluded): they track the domestic metal price."""
    m = master[master.sebi_category.fillna("").str.contains("ETF", case=False)
               & master.scheme_name.str.contains(metal, case=False)
               & ~master.scheme_name.str.contains("fof|fund of fund|multi|nifty|sensex", case=False)].copy()
    return m[m.option != "IDCW/Other"]


def build(names, master, navs, asof, log=print):
    """Return (tri_df[index,date,tri], sources_df) for the requested benchmark names."""
    composites.master = master
    navs = navs.copy()
    navs["date"] = pd.to_datetime(navs["date"]).astype("datetime64[ns]")
    cand = candidates(master)
    first = navs.groupby("amfi_code").date.min()
    last = navs.groupby("amfi_code").date.max()
    frames, src = [], []
    for name in names:
        man = indices.manual(name)
        if man is not None:
            frames.append(man.assign(index=name))
            src.append(dict(benchmark_index=name, source="manual file", amfi_code=None, scheme_name=None,
                            first_date=man.date.min().date(), er_addback=None))
            log(f"  Benchmark {name}: manual file ({len(man)} rows)")
            continue
        if name in COMMODITY:
            c = commodity_candidates(master, COMMODITY[name])
        else:
            c = cand[cand.track_key == norm(name)].copy()
        c = c[c.amfi_code.isin(first.index)]
        if len(c):
            c = c[c.amfi_code.map(last) >= asof - pd.Timedelta(days=10)]
        off = official().get(norm(name))
        if c.empty:
            if off is not None:
                pr = price_series(name)
                ext_note = ""
                if pr is not None and pr.index[-1] > off.index[-1] and pd.notna(pr.asof(off.index[-1])):
                    ext = pr[pr.index > off.index[-1]] / pr.asof(off.index[-1]) * off.iloc[-1]
                    off = pd.concat([off, ext])  # short top-up with NSE price moves (dividends ignored)
                    ext_note = " + NSE price top-up"
                off = apply_backfill(name, off)
                frames.append(pd.DataFrame({"index": name, "date": off.index, "tri": off.values}))
                src.append(dict(benchmark_index=name, source="official NSE TRI", amfi_code=None, scheme_name=None,
                                first_date=off.index[0].date(), er_addback=None, segments=f"official to {off.index[-1].date()}"))
                log(f"  Benchmark {name}: official TRI {off.index[0].date()} → {off.index[-1].date()}{ext_note}")
            elif norm(name) in LEVEL_IS_TR and price_series(name) is not None:
                lv = apply_backfill(name, price_series(name))  # NSE daily-file level already includes returns
                frames.append(pd.DataFrame({"index": name, "date": lv.index, "tri": lv.values}))
                src.append(dict(benchmark_index=name, source="NSE daily index file", amfi_code=None, scheme_name=None,
                                first_date=lv.index[0].date(), er_addback=None, segments="NSE daily index level"))
                log(f"  Benchmark {name}: NSE daily index file {lv.index[0].date()} → {lv.index[-1].date()}")
            else:
                log(f"  Benchmark {name}: no tracking scheme found")
            continue
        c["is_etf"] = c.sebi_category.str.contains("ETF", case=False)
        # main segment: Direct index fund > ETF > Regular, longest history within that preference
        c["pref"] = np.where(c.plan.eq("Direct") & ~c.is_etf, 0, np.where(c.is_etf, 1, 2))
        c["start"] = c.amfi_code.map(first)
        chain, used = [], []
        main = c.sort_values(["pref", "start"]).iloc[0]
        chain.append(main)
        # extend backwards with whichever scheme starts earliest before the current segment
        while True:
            earlier = c[(c.start < chain[-1].start - pd.Timedelta(days=30)) & ~c.amfi_code.isin([x.amfi_code for x in chain])]
            if earlier.empty:
                break
            chain.append(earlier.sort_values(["start", "pref"]).iloc[0])
        series = None
        for seg in chain:  # newest segment first; older ones are scaled to join at the splice date
            er = C.BENCH_ER_ADDBACK["commodity"] if name in COMMODITY else \
                C.BENCH_ER_ADDBACK["etf" if seg.is_etf else seg.plan.lower()]
            s = navs[navs.amfi_code == seg.amfi_code].set_index("date").nav.sort_index()
            s = s[~s.index.duplicated(keep="last")]
            g = s * np.exp(np.log1p(er) * (s.index - s.index[0]).days / 365.25)
            if series is None:
                series = g
            else:
                join = series.index[0]
                g = g[g.index <= join]
                if g.empty:
                    continue
                g = g * series.iloc[0] / g.iloc[-1]
                series = pd.concat([g[g.index < join], series])
            used.append(f"{seg.scheme_name} ({int(seg.amfi_code)}) from {s.index[0].date()}")
        tri = series / series.iloc[0] * 1000
        source = "index-tracking scheme"
        if off is not None and len(off):
            # official history up to its last date, then carried forward with the tracking scheme's daily moves
            lastd = off.index[-1]
            base = series.asof(lastd)
            ext = series[series.index > lastd] / base * off.iloc[-1] if pd.notna(base) else series.iloc[0:0]
            tri = pd.concat([off, ext])
            source = "official NSE TRI + tracking-scheme extension"
            used.insert(0, f"official NSE TRI {off.index[0].date()} → {lastd.date()}")
        frames.append(pd.DataFrame({"index": name, "date": tri.index, "tri": tri.values}))
        src.append(dict(benchmark_index=name, source=source, amfi_code=int(main.amfi_code),
                        scheme_name=main.scheme_name, first_date=tri.index[0].date(),
                        er_addback=C.BENCH_ER_ADDBACK["commodity"] if name in COMMODITY else
                        C.BENCH_ER_ADDBACK["etf" if main.is_etf else main.plan.lower()],
                        segments=" | ".join(used)))
        log(f"  Benchmark {name}: from {tri.index[0].date()} via {len(used)} segment(s)")
    built = {f["index"].iloc[0]: f.set_index("date").tri.sort_index() for f in frames if len(f)}
    comp_frames, comp_src = composites(names, built, navs, log)
    frames += comp_frames
    src += comp_src
    tri = pd.concat(frames, ignore_index=True)[["index", "date", "tri"]] if frames else \
        pd.DataFrame(columns=["index", "date", "tri"])
    return tri, pd.DataFrame(src)


# ---- composite benchmarks (substitutes for indices with no free daily data) -------------------------
# A component missing from NSE's daily file after its official history ends is carried forward with the
# NAV of a fund tracking a very similar index (Direct plan, expense added back).
EXTEND_WITH = {norm("NIFTY FINANCIAL SERVICES 3 TO 6 MONTHS DEBT"): (r"CRISIL-IBX Financial Services 3-6 Months Debt Index Fund - Direct", 0.0015)}


def component_series(name, built, navs, master_names=None):
    """Daily level for a composite component: built benchmark > official (+ NSE price/NAV top-up) > NSE daily file."""
    if name in built:
        return built[name]
    off = official().get(norm(name))
    pr = price_series(name)
    if off is not None:
        s = off
        if pr is not None and pr.index[-1] > s.index[-1] and pd.notna(pr.asof(s.index[-1])):
            s = pd.concat([s, pr[pr.index > s.index[-1]] / pr.asof(s.index[-1]) * s.iloc[-1]])
        ext = EXTEND_WITH.get(norm(name))
        if ext is not None and master_names is not None:
            codes = master_names[master_names.scheme_name.str.contains(ext[0], case=False, regex=False)].amfi_code
            n = navs[navs.amfi_code.isin(codes)]
            if len(n):
                n = n[n.amfi_code == n.groupby("amfi_code").date.min().idxmin()].set_index("date").nav.sort_index()
                n = n * np.exp(np.log1p(ext[1]) * (n.index - n.index[0]).days / 365.25)
                if n.index[-1] > s.index[-1] and pd.notna(n.asof(s.index[-1])):
                    s = pd.concat([s, n[n.index > s.index[-1]] / n.asof(s.index[-1]) * s.iloc[-1]])
        return apply_backfill(name, s)
    return apply_backfill(name, pr) if pr is not None else None


# Earlier history for an index from another official file of the SAME index. No substitute indices.
BACKFILL = {
    # same index, earlier years from NSE's daily file (official data, no substitute)
    norm("NIFTY COMPOSITE G-SEC INDEX"): [[("price", "NIFTY COMPOSITE G-SEC INDEX", 1.0)]],
}


def _level(kind, name):
    if kind == "price":
        return price_series(name)
    off = official().get(norm(name))
    pr = price_series(name)
    if off is None:
        return pr
    if pr is not None and pr.index[-1] > off.index[-1] and pd.notna(pr.asof(off.index[-1])):
        off = pd.concat([off, pr[pr.index > off.index[-1]] / pr.asof(off.index[-1]) * off.iloc[-1]])
    return off


def apply_backfill(name, s):
    if s is None or s.empty or norm(name) not in BACKFILL:
        return s
    s = s[~s.index.duplicated(keep="last")].sort_index()
    for filler in BACKFILL[norm(name)]:
        parts = [(_level(k, n), w) for k, n, w in filler]
        if any(p is None or p.empty for p, _ in parts):
            continue
        parts = [(p[~p.index.duplicated(keep="last")].sort_index(), w) for p, w in parts]
        f = parts[0][0] if len(parts) == 1 else blend_monthly(parts)
        join = s.index[0]
        f = f[f.index <= join]
        if len(f) < 2 or pd.isna(f.asof(join)):
            continue
        s = pd.concat([f[f.index < join] / f.asof(join) * s.iloc[0], s])
    return s


def blend_monthly(parts):
    """Fixed weights reset at each month-end; daily values in between (NSE hybrid-index convention)."""
    idx = sorted(set().union(*[p.index for p, _ in parts]))
    start = max(p.index[0] for p, _ in parts)
    idx = pd.DatetimeIndex([d for d in idx if d >= start])
    al = [(p.reindex(idx).ffill(), w) for p, w in parts]
    month = idx.to_period("M")
    out, level = [], 1000.0
    anchor = {i: s.iloc[0] for i, (s, _) in enumerate(al)}
    base = level
    for k in range(len(idx)):
        if k > 0 and month[k] != month[k - 1]:          # reset at the previous month-end
            base = out[-1]
            anchor = {i: s.iloc[k - 1] for i, (s, _) in enumerate(al)}
        v = base * sum(w * s.iloc[k] / anchor[i] for i, (s, w) in enumerate(al))
        out.append(v)
    return pd.Series(out, index=idx)


def composites(names, built, navs, log=print):
    f = C.CONFIG / "composite_benchmarks.csv"
    if not f.exists():
        return [], []
    cfg = pd.read_csv(f)
    master_names = getattr(composites, "master", None)
    frames, src = [], []
    for bname, g in cfg.groupby("benchmark", sort=False):
        if bname not in names:
            continue
        parts, missing = [], []
        for r in g.itertuples():
            s = component_series(r.component, built, navs, master_names)
            if s is None or s.empty:
                missing.append(r.component)
            else:
                parts.append((s[~s.index.duplicated(keep="last")].sort_index(), float(r.weight)))
        if missing:
            log(f"  Benchmark {bname[:60]}: missing component(s) {missing}")
            continue
        ser = parts[0][0] / parts[0][0].iloc[0] * 1000 if len(parts) == 1 else blend_monthly(parts)
        frames.append(pd.DataFrame({"index": bname, "date": ser.index, "tri": ser.values}))
        src.append(dict(benchmark_index=bname, source="composite of official NSE indices", amfi_code=None,
                        scheme_name=None, first_date=ser.index[0].date(), er_addback=None,
                        segments=" + ".join(f"{r.component} {r.weight:g}" for r in g.itertuples())))
        log(f"  Benchmark {bname[:60]}: composite from {ser.index[0].date()}")
    return frames, src
