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


COMMODITY = {"DOMESTIC GOLD PRICE": "gold", "DOMESTIC SILVER PRICE": "silver"}


def commodity_candidates(master, metal):
    """Gold / Silver ETFs only (FoFs and multi-asset excluded): they track the domestic metal price."""
    m = master[master.sebi_category.fillna("").str.contains("ETF", case=False)
               & master.scheme_name.str.contains(metal, case=False)
               & ~master.scheme_name.str.contains("fof|fund of fund|multi|nifty|sensex", case=False)].copy()
    return m[m.option != "IDCW/Other"]


def build(names, master, navs, asof, log=print):
    """Return (tri_df[index,date,tri], sources_df) for the requested benchmark names."""
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
        c = c[c.amfi_code.map(last) >= asof - pd.Timedelta(days=10)]
        if c.empty:
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
        frames.append(pd.DataFrame({"index": name, "date": tri.index, "tri": tri.values}))
        src.append(dict(benchmark_index=name, source="index-tracking scheme", amfi_code=int(main.amfi_code),
                        scheme_name=main.scheme_name, first_date=tri.index[0].date(),
                        er_addback=C.BENCH_ER_ADDBACK["commodity"] if name in COMMODITY else
                        C.BENCH_ER_ADDBACK["etf" if main.is_etf else main.plan.lower()],
                        segments=" | ".join(used)))
        log(f"  Benchmark {name}: from {tri.index[0].date()} via {len(used)} segment(s)")
    tri = pd.concat(frames, ignore_index=True)[["index", "date", "tri"]] if frames else \
        pd.DataFrame(columns=["index", "date", "tri"])
    return tri, pd.DataFrame(src)
