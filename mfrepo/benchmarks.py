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
        c = cand[cand.track_key == norm(name)].copy()
        c = c[c.amfi_code.isin(first.index)]
        c = c[c.amfi_code.map(last) >= asof - pd.Timedelta(days=10)]
        if c.empty:
            log(f"  Benchmark {name}: no tracking scheme found")
            continue
        is_etf = c.sebi_category.str.contains("ETF", case=False)
        # prefer Direct index funds, then ETFs, then Regular; longest history first
        c["pref"] = np.where(c.plan.eq("Direct") & ~is_etf, 0, np.where(is_etf, 1, 2))
        c["start"] = c.amfi_code.map(first)
        best = c.sort_values(["start", "pref"]).iloc[0] if (c.start.min() < asof - pd.DateOffset(years=5)) \
            else c.sort_values(["pref", "start"]).iloc[0]
        er = C.BENCH_ER_ADDBACK["etf" if "ETF" in str(best.sebi_category).upper() else best.plan.lower()]
        s = navs[navs.amfi_code == best.amfi_code].set_index("date").nav.sort_index()
        s = s[~s.index.duplicated(keep="last")]
        yrs = (s.index - s.index[0]).days / 365.25
        tri = s / s.iloc[0] * 1000 * np.exp(np.log1p(er) * yrs)
        frames.append(pd.DataFrame({"index": name, "date": tri.index, "tri": tri.values}))
        src.append(dict(benchmark_index=name, source="index-tracking scheme", amfi_code=int(best.amfi_code),
                        scheme_name=best.scheme_name, first_date=s.index[0].date(), er_addback=er))
        log(f"  Benchmark {name}: {best.scheme_name} ({best.amfi_code}) from {s.index[0].date()}")
    tri = pd.concat(frames, ignore_index=True)[["index", "date", "tri"]] if frames else \
        pd.DataFrame(columns=["index", "date", "tri"])
    return tri, pd.DataFrame(src)
