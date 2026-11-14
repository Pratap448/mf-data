"""Benchmark Total Return Index (TRI) history from NSE Indices (niftyindices.com).

The site serves data through a JSON endpoint used by its own 'Historical Data' page. If it ever
blocks the request, drop a CSV with columns Date,TRI into manual/tri/<INDEX NAME>.csv and it will
be used instead (e.g. manual/tri/NIFTY 50.csv).
"""
import json, time, datetime as dt
import pandas as pd, requests
from . import config as C

URL = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"


def _session():
    s = requests.Session()
    s.headers.update({**C.HTTP_HEADERS, "Content-Type": "application/json; charset=UTF-8",
                      "Accept": "application/json, text/javascript, */*; q=0.01",
                      "Origin": "https://www.niftyindices.com",
                      "Referer": "https://www.niftyindices.com/reports/historical-data",
                      "X-Requested-With": "XMLHttpRequest"})
    try:
        s.get("https://www.niftyindices.com/reports/historical-data", timeout=60)  # sets cookies
    except Exception:
        pass
    return s


def _fetch_year(s, name, start, end):
    cinfo = "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
        name, start.strftime("%d-%b-%Y"), end.strftime("%d-%b-%Y"), name)
    r = s.post(URL, data=json.dumps({"cinfo": cinfo}), timeout=90)
    r.raise_for_status()
    try:
        rows = json.loads(r.json()["d"])
    except Exception:
        raise RuntimeError(f"NSE sent non-JSON (HTTP {r.status_code}, {len(r.text)} chars): {r.text[:200]!r}")
    if not rows:
        return pd.DataFrame(columns=["date", "tri"])
    df = pd.DataFrame(rows)
    dcol = next(c for c in df.columns if "date" in c.lower())
    vcol = next(c for c in df.columns if "return" in c.lower())
    out = pd.DataFrame({"date": pd.to_datetime(df[dcol], errors="coerce", dayfirst=True),
                        "tri": pd.to_numeric(df[vcol].astype(str).str.replace(",", ""), errors="coerce")})
    return out.dropna()


def manual(name):
    f = C.MANUAL_TRI / f"{name}.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f)
    df.columns = [c.strip().lower() for c in df.columns]
    return pd.DataFrame({"date": pd.to_datetime(df["date"], dayfirst=True, errors="coerce"),
                         "tri": pd.to_numeric(df["tri"], errors="coerce")}).dropna()


def tri_history(names, start, end, log=print):
    s, frames = _session(), []
    for name in names:
        m = manual(name)
        if m is not None:
            log(f"  TRI {name}: manual file ({len(m)} rows)")
            frames.append(m.assign(index=name)); continue
        parts, y = [], start
        try:
            while y <= end:
                e = min(dt.date(y.year, 12, 31), end)
                parts.append(_fetch_year(s, name, y, e)); y = e + dt.timedelta(days=1); time.sleep(1)
            df = pd.concat(parts, ignore_index=True)
            log(f"  TRI {name}: {len(df)} rows")
            frames.append(df.assign(index=name))
        except Exception as ex:
            log(f"  TRI {name}: FAILED ({ex}). Add manual/tri/{name}.csv to cover it.")
    if not frames:
        return pd.DataFrame(columns=["index", "date", "tri"])
    return pd.concat(frames, ignore_index=True)[["index", "date", "tri"]]
