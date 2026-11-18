"""Analytics engine: every return / risk / benchmark / category measure, for ANY period.

Works on plain pandas Series (date-indexed levels: NAV, TRI, category index). The repo stores the
raw daily data; this module computes everything on demand, so new ratios never need a data change.

    from mfrepo.analytics import Repo, metrics, compare
    r = Repo("/path/to/mf-data")                 # local clone
    nav = r.nav(118668)                          # daily NAV series
    bm  = r.benchmark_of(118668)                 # its benchmark TRI series
    cat = r.category_of(118668)                  # its category-average index
    metrics(nav, "2019-04-01", "2024-03-31", bm=bm, cat=cat)   # every measure for that window
    compare([118668, 120505], "3Y", r=r)         # side-by-side table incl. category avg & rank

Conventions
- Returns in %, CAGR for periods > 1 year, absolute otherwise (AMFI/SEBI convention).
- Risk on monthly returns by default (freq="M"); daily ("D") and weekly ("W") also supported.
- Risk-free rate: config.RF_RATE (annual), converted to the return frequency.
"""
from __future__ import annotations
import re, math, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd

try:
    from . import config as C
    RF = C.RF_RATE
except Exception:  # usable standalone
    RF = 0.065

PPY = {"D": 252, "W": 52, "M": 12}           # periods per year
TRAILING = ["1M", "3M", "6M", "YTD", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "SI"]


# --------------------------------------------------------------------------------------------- dates
def _ts(x):
    return pd.Timestamp(x).normalize() if x is not None else None


def period_start(asof, period, inception=None):
    """'1M','3M','6M','YTD','1Y'...'10Y','SI', or an explicit date -> start date."""
    asof = _ts(asof)
    if period is None:
        return inception
    p = str(period).upper()
    if p == "YTD":
        return pd.Timestamp(asof.year - 1, 12, 31)
    if p == "SI":
        return inception
    m = re.fullmatch(r"(\d+)([DWMY])", p)
    if m:
        n, u = int(m.group(1)), m.group(2)
        return asof - {"D": pd.DateOffset(days=n), "W": pd.DateOffset(weeks=n),
                       "M": pd.DateOffset(months=n), "Y": pd.DateOffset(years=n)}[u]
    return _ts(period)


def resolve_window(s, start=None, end=None):
    """start may be a period code ('3Y') or a date; end defaults to the series' last date."""
    s = clean(s)
    end = _ts(end) if end is not None else s.index[-1]
    if start is None or str(start).upper() == "SI":
        st = s.index[0]
    elif re.fullmatch(r"\d+[DWMY]|YTD", str(start).upper()):
        st = period_start(end, start, s.index[0])
    else:
        st = _ts(start)
    return st, end


# --------------------------------------------------------------------------------------------- basics
def clean(s):
    s = pd.Series(s).dropna()
    s = s[s > 0]
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def value_on(s, d, tol_days=7):
    """Level on or before d (None if no data within tol_days before d)."""
    s = s[s.index <= d]
    if s.empty or (d - s.index[-1]).days > tol_days:
        return None
    return float(s.iloc[-1])


def covers(s, start, tol_days=7):
    return len(s) and s.index[0] <= start + pd.Timedelta(days=tol_days)


def period_return(s, start, end=None, annualise=True):
    """Point-to-point return in %. CAGR if > 1 year (and annualise=True). None if not covered."""
    s = clean(s)
    st, en = resolve_window(s, start, end)
    if not covers(s, st):
        return None
    a, b = value_on(s, st), value_on(s, en)
    if a is None or b is None:
        return None
    yrs = (en - st).days / 365.25
    if annualise and yrs > 1.0001:
        return ((b / a) ** (1 / yrs) - 1) * 100
    return (b / a - 1) * 100


def trailing_returns(s, asof=None, periods=TRAILING):
    s = clean(s)
    asof = _ts(asof) if asof is not None else s.index[-1]
    out = {}
    for p in periods:
        st = period_start(asof, p, s.index[0])
        out[f"ret_{p.lower()}"] = period_return(s, st, asof) if st is not None else None
    return out


def calendar_returns(s, years=None, fy=False):
    """Calendar-year (or financial-year Apr-Mar if fy=True) returns in %, partial years excluded."""
    s = clean(s)
    out = {}
    first, last = s.index[0], s.index[-1]
    yrs = years or range(first.year, last.year + 1)
    for y in yrs:
        st = pd.Timestamp(y - 1, 12, 31) if not fy else pd.Timestamp(y - 1, 3, 31)
        en = pd.Timestamp(y, 12, 31) if not fy else pd.Timestamp(y, 3, 31)
        if covers(s, st) and last >= en - pd.Timedelta(days=7):
            out[(f"FY{y}" if fy else str(y))] = period_return(s, st, en, annualise=False)
    return out


def returns(s, freq="M", start=None, end=None):
    """Periodic simple returns on a regular grid (D=trading days present, W=Fri, M=month-end)."""
    s = clean(s)
    st, en = resolve_window(s, start, end)
    s = s[(s.index >= st - pd.Timedelta(days=10)) & (s.index <= en)]
    if freq == "D":
        lv = s[s.index >= st - pd.Timedelta(days=10)]
        r = lv.pct_change()
        return r[r.index > st].dropna()
    rule = {"W": "W-FRI", "M": "ME"}[freq]
    lv = s.resample(rule).last()
    # first point = level at the window start, so the first period is complete
    base = value_on(s, st)
    if base is None:
        return pd.Series(dtype=float)
    lv = lv[lv.index > st]
    lv = pd.concat([pd.Series([base], index=[st]), lv])
    return lv.pct_change().dropna()


def _rf_per(freq, rf=None):
    rf = RF if rf is None else rf
    return (1 + rf) ** (1 / PPY[freq]) - 1


# --------------------------------------------------------------------------------------------- risk
def drawdown_stats(s, start=None, end=None):
    s = clean(s)
    st, en = resolve_window(s, start, end)
    w = s[(s.index >= st) & (s.index <= en)]
    if len(w) < 2:
        return {}
    peak = w.cummax()
    dd = w / peak - 1
    trough = dd.idxmin()
    peak_date = w[:trough].idxmax()
    rec = w[(w.index > trough) & (w >= w[peak_date])]
    rec_date = rec.index[0] if len(rec) else None
    # longest time under water (peak to recovery, or to end if not recovered)
    under = dd < 0
    longest, cur, start_uw = 0, 0, None
    for d, u in under.items():
        if u:
            start_uw = start_uw or d
            cur = (d - start_uw).days
            longest = max(longest, cur)
        else:
            start_uw = None
    ulcer = float(np.sqrt(((dd * 100) ** 2).mean()))
    return {"max_drawdown": float(dd.min() * 100), "dd_peak_date": peak_date.date(), "dd_trough_date": trough.date(),
            "dd_recovery_date": rec_date.date() if rec_date is not None else None,
            "dd_days_to_trough": (trough - peak_date).days,
            "dd_days_to_recover": (rec_date - trough).days if rec_date is not None else None,
            "longest_underwater_days": longest, "ulcer_index": ulcer,
            "current_drawdown": float(dd.iloc[-1] * 100)}


def risk_measures(s, start=None, end=None, freq="M", rf=None):
    """Stand-alone risk / risk-adjusted measures for one series over [start, end]."""
    r = returns(s, freq, start, end)
    n = len(r)
    out = {"obs": n}
    if n < (12 if freq == "M" else 26 if freq == "W" else 60):
        return out
    k = PPY[freq]
    rfp = _rf_per(freq, rf)
    ann_ret = (1 + r).prod() ** (k / n) - 1
    vol = r.std(ddof=1) * math.sqrt(k)
    ex = r - rfp
    downside = np.minimum(r - rfp, 0)
    dd_dev = math.sqrt((downside ** 2).mean()) * math.sqrt(k)
    var95 = -np.percentile(r, 5)
    cvar95 = -r[r <= np.percentile(r, 5)].mean()
    gains, losses = (r - rfp).clip(lower=0).sum(), (rfp - r).clip(lower=0).sum()
    rfa = RF if rf is None else rf
    dds = drawdown_stats(s, start, end)
    out.update({
        "ann_return": ann_ret * 100, "std_dev": vol * 100, "downside_dev": dd_dev * 100,
        "sharpe": (ann_ret - rfa) / vol if vol else None,
        "sortino": (ann_ret - rfa) / dd_dev if dd_dev else None,
        "skewness": float(r.skew()), "kurtosis": float(r.kurt()),
        "var_95": var95 * 100, "cvar_95": cvar95 * 100,
        "omega": gains / losses if losses else None,
        "pct_positive_periods": float((r > 0).mean() * 100),
        "best_period": float(r.max() * 100), "worst_period": float(r.min() * 100),
        "mean_excess_per_period": float(ex.mean() * 100),
    })
    out.update(dds)
    if dds.get("max_drawdown"):
        out["calmar"] = ann_ret * 100 / abs(dds["max_drawdown"])
    return out


def relative_measures(s, bm, start=None, end=None, freq="M", rf=None, prefix=""):
    """Fund vs benchmark (or vs category index): beta, alpha, R2, TE, IR, captures, batting avg..."""
    f, b = returns(s, freq, start, end), returns(bm, freq, start, end)
    j = pd.concat([f.rename("f"), b.rename("b")], axis=1, join="inner").dropna()
    n = len(j)
    min_obs = 12 if freq == "M" else 26 if freq == "W" else 60
    if n < min_obs:
        return {f"{prefix}obs_rel": n}
    k = PPY[freq]
    rfp = _rf_per(freq, rf)
    ef, eb = j.f - rfp, j.b - rfp
    beta = float(np.cov(ef, eb, ddof=1)[0, 1] / eb.var(ddof=1))
    alpha = float((ef.mean() - beta * eb.mean()) * k * 100)
    corr = float(j.f.corr(j.b))
    act = j.f - j.b
    te = float(act.std(ddof=1) * math.sqrt(k))
    fa = (1 + j.f).prod() ** (k / n) - 1
    ba = (1 + j.b).prod() ** (k / n) - 1
    rfa = RF if rf is None else rf
    fvol, bvol = j.f.std(ddof=1) * math.sqrt(k), j.b.std(ddof=1) * math.sqrt(k)

    def geo(x):
        return (1 + x).prod() ** (k / len(x)) - 1 if len(x) else None
    up, dn = j[j.b > 0], j[j.b < 0]
    upc = geo(up.f) / geo(up.b) * 100 if len(up) and geo(up.b) else None
    dnc = geo(dn.f) / geo(dn.b) * 100 if len(dn) and geo(dn.b) else None
    # arithmetic (Morningstar-style period average) captures as an alternative
    upa = up.f.mean() / up.b.mean() * 100 if len(up) else None
    dna = dn.f.mean() / dn.b.mean() * 100 if len(dn) else None
    out = {
        "obs_rel": n, "beta": beta, "alpha": alpha, "r_squared": corr ** 2 * 100, "correlation": corr,
        "tracking_error": te * 100, "active_return": (fa - ba) * 100,
        "information_ratio": (fa - ba) / te if te else None,
        "treynor": (fa - rfa) / beta * 100 if beta else None,
        "m2": ((fa - rfa) / fvol * bvol + rfa) * 100 if fvol else None,
        "up_capture": upc, "down_capture": dnc,
        "capture_ratio": upc / dnc if upc is not None and dnc not in (None, 0) else None,
        "up_capture_arith": upa, "down_capture_arith": dna,
        "batting_avg": float((act > 0).mean() * 100),
        "up_batting_avg": float((up.f > up.b).mean() * 100) if len(up) else None,
        "down_batting_avg": float((dn.f > dn.b).mean() * 100) if len(dn) else None,
        "bm_ann_return": ba * 100, "bm_std_dev": bvol * 100,
        "excess_return": (fa - ba) * 100,
    }
    return {prefix + k_: v for k_, v in out.items()}


def rolling_returns(s, window="3Y", start=None, end=None, step="D", bm=None):
    """Rolling CAGR (window > 1Y) or absolute return, sampled daily/weekly/monthly.
    Returns (series, stats). stats include % of windows beating the benchmark when bm is given."""
    s = clean(s)
    st, en = resolve_window(s, start, end)
    m = re.fullmatch(r"(\d+)([MY])", window.upper())
    off = pd.DateOffset(years=int(m.group(1))) if m.group(2) == "Y" else pd.DateOffset(months=int(m.group(1)))
    yrs = int(m.group(1)) if m.group(2) == "Y" else int(m.group(1)) / 12
    daily = s.resample("D").last().ffill()
    grid = {"D": daily.index, "W": daily.resample("W-FRI").last().index, "M": daily.resample("ME").last().index}[step]
    ends = grid[(grid >= max(st, s.index[0]) + off) & (grid <= en)]
    if not len(ends):
        return pd.Series(dtype=float), {}
    starts = ends - off
    a, b = daily.reindex(starts).to_numpy(), daily.reindex(ends).to_numpy()
    rr = (b / a) ** (1 / yrs) - 1 if yrs > 1 else b / a - 1
    ser = pd.Series(rr * 100, index=ends).dropna()
    stats = {"roll_obs": len(ser), "roll_avg": ser.mean(), "roll_median": ser.median(), "roll_min": ser.min(),
             "roll_max": ser.max(), "roll_std": ser.std(), "roll_pct_positive": (ser > 0).mean() * 100,
             "roll_pct_above_6": (ser > 6).mean() * 100, "roll_pct_above_10": (ser > 10).mean() * 100,
             "roll_pct_above_12": (ser > 12).mean() * 100, "roll_pct_above_15": (ser > 15).mean() * 100}
    if bm is not None:
        bs, _ = rolling_returns(bm, window, start, end, step)
        j = pd.concat([ser.rename("f"), bs.rename("b")], axis=1, join="inner").dropna()
        if len(j):
            stats.update({"roll_bm_avg": j.b.mean(), "roll_pct_beat_bm": (j.f > j.b).mean() * 100,
                          "roll_avg_outperformance": (j.f - j.b).mean()})
    return ser, stats


# --------------------------------------------------------------------------------------------- XIRR
def xirr(cashflows):
    """cashflows: list of (date, amount) — investments negative, redemptions/current value positive."""
    cf = sorted((pd.Timestamp(d), float(a)) for d, a in cashflows if a)
    if not cf or all(a >= 0 for _, a in cf) or all(a <= 0 for _, a in cf):
        return None
    t0 = cf[0][0]
    ts = np.array([(d - t0).days / 365.0 for d, _ in cf])
    am = np.array([a for _, a in cf])

    def npv(r):
        return float((am / (1 + r) ** ts).sum())
    lo, hi = -0.9999, 10.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if abs(fm) < 1e-7:
            break
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return mid * 100


def mirror_xirr(cashflows, level, value_date=None):
    """XIRR the same cash flows would have earned in `level` (a benchmark / category series).
    Each investment buys units at that day's level, each withdrawal sells units; the remaining
    units are valued at value_date. Use for Benchmark XIRR and Category XIRR."""
    level = clean(level)
    units = 0.0
    flows = []
    for d, a in sorted(cashflows, key=lambda x: pd.Timestamp(x[0])):
        d = pd.Timestamp(d)
        px = value_on(level, d, tol_days=10)
        if px is None:
            return None
        units += -a / px      # investment (negative a) buys units
        flows.append((d, a))
    vd = _ts(value_date) if value_date is not None else level.index[-1]
    pv = value_on(level, vd, tol_days=10)
    if pv is None:
        return None
    flows.append((vd, units * pv))
    return xirr(flows)


def sip_returns(s, start, end=None, amount=10000, day=1):
    """Monthly SIP on `day` of each month: invested, value, XIRR, absolute gain."""
    s = clean(s)
    st, en = resolve_window(s, start, end)
    dates = pd.date_range(st, en, freq="MS") + pd.Timedelta(days=day - 1)
    cf, units = [], 0.0
    for d in dates:
        px = value_on(s, d, 10)
        if px is None:
            continue
        units += amount / px
        cf.append((d, -amount))
    if not cf:
        return {}
    val = units * value_on(s, en, 10)
    invested = amount * len(cf)
    return {"sip_installments": len(cf), "sip_invested": invested, "sip_value": val,
            "sip_gain_pct": (val / invested - 1) * 100, "sip_xirr": xirr(cf + [(en, val)])}


# --------------------------------------------------------------------------------------------- all-in-one
def metrics(s, start=None, end=None, bm=None, cat=None, freq="M", rf=None, rolling=("1Y", "3Y", "5Y"),
            calendar=False):
    """Every measure for one series over [start, end]: returns, risk, vs benchmark, vs category."""
    s = clean(s)
    st, en = resolve_window(s, start, end)
    out = {"start": st.date(), "end": en.date(), "inception": s.index[0].date(),
           "period_return": period_return(s, st, en)}
    out.update(trailing_returns(s, en))
    out.update(risk_measures(s, st, en, freq, rf))
    if bm is not None and len(clean(bm)):
        out.update(relative_measures(s, bm, st, en, freq, rf))
        out["bm_period_return"] = period_return(bm, st, en)
        for p, v in trailing_returns(bm, en).items():
            out["bm_" + p] = v
    if cat is not None and len(clean(cat)):
        out.update(relative_measures(s, cat, st, en, freq, rf, prefix="cat_"))
        out["cat_period_return"] = period_return(cat, st, en)
    for w in rolling or ():
        _, stt = rolling_returns(s, w, st, en, "D", bm)
        out.update({f"{k}_{w.lower()}": v for k, v in stt.items()})
    if calendar:
        out.update({f"cy_{k}": v for k, v in calendar_returns(s).items()})
    return out


# Direction for ranking: +1 higher is better, -1 lower is better
RANK_DIRECTION = {"ret": 1, "period_return": 1, "ann_return": 1, "sharpe": 1, "sortino": 1, "calmar": 1,
                  "omega": 1, "alpha": 1, "information_ratio": 1, "treynor": 1, "m2": 1, "capture_ratio": 1,
                  "up_capture": 1, "batting_avg": 1, "roll_avg": 1, "roll_pct_beat_bm": 1, "excess_return": 1,
                  "std_dev": -1, "downside_dev": -1, "max_drawdown": 1, "var_95": -1, "cvar_95": -1,
                  "down_capture": -1, "tracking_error": -1, "ulcer_index": -1, "beta": -1}


def direction(col):
    c = col.replace("cat_", "")
    for k, v in RANK_DIRECTION.items():
        if c == k or c.startswith(k + "_") or c.startswith(k):
            return v
    return 0


def rank_table(df, cols=None, group=None, min_peers=4):
    """Adds <col>_rank, <col>_of, <col>_pctile, <col>_quartile for each column (within `group`).
    rank 1 = best (direction from RANK_DIRECTION); quartile 1 = top quarter."""
    df = df.copy()
    cols = cols or [c for c in df.columns if direction(c) and pd.api.types.is_numeric_dtype(df[c])]
    keys = df[group] if group else pd.Series(0, index=df.index)
    new = {}
    for c in cols:
        d = direction(c)
        if not d or c not in df:
            continue
        v = pd.to_numeric(df[c], errors="coerce")
        n = v.groupby(keys).transform("count")
        rk = v.groupby(keys).rank(ascending=(d < 0), method="min")
        ok = n >= min_peers
        new[c + "_rank"] = rk.where(ok)
        new[c + "_of"] = n.where(ok)
        new[c + "_pctile"] = ((1 - (rk - 1) / n) * 100).where(ok)
        new[c + "_quartile"] = (np.floor((rk - 1) / n * 4) + 1).clip(1, 4).where(ok)
    return pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)


# --------------------------------------------------------------------------------------------- repo access
class Repo:
    """Read access to a local clone of the data repo."""

    def __init__(self, root="."):
        self.root = Path(root)
        self.d = self.root / "data"
        self._nav = None
        self._bm = None
        self._cat = None
        self._master = None

    @property
    def master(self):
        if self._master is None:
            self._master = pd.read_csv(self.d / "scheme_master.csv", low_memory=False)
        return self._master

    def _load_nav(self):
        if self._nav is None:
            files = sorted((self.d / "nav").glob("nav_*.parquet"))
            self._nav = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else \
                pd.DataFrame(columns=["amfi_code", "date", "nav"])
            self._nav["date"] = pd.to_datetime(self._nav["date"])
            self._nav = self._nav.set_index("amfi_code").sort_index()
        return self._nav

    def nav(self, code):
        n = self._load_nav()
        code = int(code)
        if code not in n.index:
            sib = self.master.set_index("amfi_code").get("nav_source_code")
            if sib is not None and code in sib.index and pd.notna(sib.loc[code]):
                code = int(sib.loc[code])
        if code not in n.index:
            return pd.Series(dtype=float)
        g = n.loc[[code]]
        return clean(pd.Series(g["nav"].to_numpy(), index=g["date"].to_numpy()))

    def benchmark(self, name):
        if self._bm is None:
            b = pd.read_csv(self.d / "benchmark_tri.csv.gz", parse_dates=["date"])
            self._bm = {k: clean(g.set_index("date").tri) for k, g in b.groupby("index")}
        return self._bm.get(name, pd.Series(dtype=float))

    def benchmark_of(self, code):
        row = self.master[self.master.amfi_code == int(code)]
        return self.benchmark(row.benchmark_index.iloc[0]) if len(row) and pd.notna(row.benchmark_index.iloc[0]) \
            else pd.Series(dtype=float)

    def category(self, peer_group):
        if self._cat is None:
            f = self.d / "category_index.parquet"
            c = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=["peer_group", "date", "level"])
            c["date"] = pd.to_datetime(c["date"])
            self._cat = {k: clean(g.set_index("date").level) for k, g in c.groupby("peer_group")}
        return self._cat.get(peer_group, pd.Series(dtype=float))

    def category_of(self, code):
        row = self.master[self.master.amfi_code == int(code)]
        return self.category(row.peer_group.iloc[0]) if len(row) and "peer_group" in row and \
            pd.notna(row.peer_group.iloc[0]) else pd.Series(dtype=float)

    def peers(self, code, growth_only=True):
        row = self.master[self.master.amfi_code == int(code)]
        if not len(row):
            return []
        m = self.master[self.master.peer_group == row.peer_group.iloc[0]]
        if growth_only:
            m = m[m.option == "Growth"]
        return m.amfi_code.tolist()


def compare(codes, start=None, end=None, r: Repo = None, freq="M", with_peers=False, bm_name=None):
    """Side-by-side metrics for several schemes over the same window, plus category rank.
    with_peers=True ranks each fund against its whole category for this exact window."""
    rows = []
    for c in codes:
        nav = r.nav(c)
        if nav.empty:
            continue
        bm = r.benchmark(bm_name) if bm_name else r.benchmark_of(c)
        m = metrics(nav, start, end, bm=bm, cat=r.category_of(c), freq=freq)
        m["amfi_code"] = c
        rows.append(m)
    df = pd.DataFrame(rows)
    if with_peers and len(df):
        out = []
        for c in df.amfi_code:
            peers = r.peers(c)
            pm = []
            for p in peers:
                nv = r.nav(p)
                if nv.empty:
                    continue
                x = metrics(nv, start, end, bm=r.benchmark_of(p), freq=freq, rolling=())
                x["amfi_code"] = p
                pm.append(x)
            pdf = rank_table(pd.DataFrame(pm))
            out.append(pdf[pdf.amfi_code == c])
        df = df.merge(pd.concat(out)[["amfi_code"] + [k for k in pd.concat(out).columns
                                                      if k.endswith(("_rank", "_of", "_quartile", "_pctile"))]],
                      on="amfi_code", how="left")
    return df
