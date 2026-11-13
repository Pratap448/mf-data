"""Return and risk calculations on daily NAV / TRI series (pandas Series indexed by date)."""
import numpy as np, pandas as pd
from . import config as C


def _val_on(s, d):
    """Last value on or before date d (None if series starts after d)."""
    s = s[s.index <= d]
    return None if s.empty else s.iloc[-1]


def point_return(s, asof, years=None, start=None):
    """Annualised (CAGR) for >1Y, absolute otherwise. Needs data reaching back to the start date."""
    if start is None:
        start = asof - pd.DateOffset(years=years)
    if s.index[0] > start + pd.Timedelta(days=7):
        return None
    a, b = _val_on(s, start), _val_on(s, asof)
    if a is None or b is None or a <= 0:
        return None
    yrs = (asof - start).days / 365.25
    return ((b / a) ** (1 / yrs) - 1) * 100 if yrs > 1.01 else (b / a - 1) * 100


def period_returns(s, asof):
    ytd_start = pd.Timestamp(asof.year - 1, 12, 31)
    return {"ret_ytd": point_return(s, asof, start=ytd_start), "ret_1y": point_return(s, asof, 1),
            "ret_3y": point_return(s, asof, 3), "ret_5y": point_return(s, asof, 5)}


def rolling_avg(s, asof, window=C.ROLL_WINDOW_YEARS, span=C.ROLL_DATA_YEARS):
    """Average of daily rolling `window`-year CAGRs whose windows lie inside the last `span` years.
    Requires a full `span`-year record."""
    first = asof - pd.DateOffset(years=span)
    if s.index[0] > first + pd.Timedelta(days=7):
        return None
    s = s[s.index >= first - pd.Timedelta(days=7)]
    daily = s.resample("D").last().ffill()
    ends = daily.index[(daily.index >= first + pd.DateOffset(years=window)) & (daily.index <= asof)]
    starts = ends - pd.DateOffset(years=window)
    a = daily.reindex(starts).to_numpy()
    b = daily.reindex(ends).to_numpy()
    r = pd.Series((b / a) ** (1 / window) - 1).dropna()
    return None if r.empty else r.mean() * 100


def monthly(s, asof, months):
    m = s[s.index <= asof].resample("ME").last()
    r = m.pct_change().dropna()
    return r.iloc[-months:] if len(r) >= months else None


def risk_stats(fs, bs, asof, months=C.RISK_MONTHS, rf=C.RF_RATE):
    out = dict(sd_3y=None, sharpe_3y=None, beta_3y=None, alpha_3y=None, up_capture=None,
               down_capture=None, capture_ratio=None)
    f = monthly(fs, asof, months)
    if f is None:
        return out
    rfm = (1 + rf) ** (1 / 12) - 1
    ann = (1 + f).prod() ** (12 / len(f)) - 1
    sd = f.std(ddof=1) * np.sqrt(12)
    out["sd_3y"] = sd * 100
    out["sharpe_3y"] = (ann - rf) / sd if sd > 0 else None
    if bs is None:
        return out
    b = monthly(bs, asof, months)
    if b is None:
        return out
    j = pd.concat([f.rename("f"), b.rename("b")], axis=1, join="inner").dropna()
    if len(j) < months * 0.9:
        return out
    ef, eb = j.f - rfm, j.b - rfm
    beta = np.cov(ef, eb, ddof=1)[0, 1] / eb.var(ddof=1)
    out["beta_3y"] = beta
    out["alpha_3y"] = (ef.mean() - beta * eb.mean()) * 12 * 100      # Jensen's alpha, annualised %

    def geo(x):
        return (1 + x).prod() ** (12 / len(x)) - 1 if len(x) else None
    up, dn = j[j.b > 0], j[j.b < 0]
    if len(up) and geo(up.b):
        out["up_capture"] = geo(up.f) / geo(up.b) * 100
    if len(dn) and geo(dn.b):
        out["down_capture"] = geo(dn.f) / geo(dn.b) * 100
    if out["up_capture"] is not None and out["down_capture"] is not None and out["down_capture"] > 0:
        out["capture_ratio"] = out["up_capture"] / out["down_capture"]   # NA if fund rose in down months
    return out


def rank_quartile(values):
    """values: Series (higher = better). Returns rank (1 = best), count, percentile, quartile."""
    v = values.dropna()
    n = len(v)
    if n < C.MIN_PEERS:
        return pd.DataFrame(index=values.index, columns=["rank", "count", "pctile", "quartile"])
    rk = v.rank(ascending=False, method="min")
    df = pd.DataFrame({"rank": rk, "count": n})
    df["pctile"] = (rk / n * 100).round(0)
    df["quartile"] = (np.floor((rk - 1) * 4 / n) + 1).clip(1, 4).astype(int)
    return df.reindex(values.index)
