"""Equity index PRICE history from NSE's daily index snapshot files (nsearchives.nseindia.com).

One CSV per trading day lists the closing value of every NSE index. Files are fetched once and the
result is kept in data/index_price.csv.gz, so later runs only download the days since the last run.
Old index names (e.g. 'CNX Nifty', 'CNX Nifty Junior') are mapped to today's names.
"""
import io, re, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, requests
from . import config as C

URLS = ["https://nsearchives.nseindia.com/content/indices/ind_close_all_{d}.csv",
        "https://archives.nseindia.com/content/indices/ind_close_all_{d}.csv"]
OUT_FILE = "index_price.csv.gz"
ALIASES = {"S&P CNX NIFTY": "NIFTY 50", "CNX NIFTY": "NIFTY 50", "NIFTY": "NIFTY 50",
           "CNX NIFTY JUNIOR": "NIFTY NEXT 50", "NIFTY JUNIOR": "NIFTY NEXT 50",
           "CNX 100": "NIFTY 100", "CNX 200": "NIFTY 200", "S&P CNX 500": "NIFTY 500", "CNX 500": "NIFTY 500",
           "CNX MIDCAP": "NIFTY MIDCAP 100", "NIFTY MIDCAP 100": "NIFTY MIDCAP 100",
           "NIFTY500 MULTICAP 50:25:25": "NIFTY 500 MULTICAP 50:25:25",
           "NIFTY MIDCAP150": "NIFTY MIDCAP 150", "NIFTY SMALLCAP250": "NIFTY SMALLCAP 250",
           "NIFTY LARGEMIDCAP250": "NIFTY LARGEMIDCAP 250"}


def clean_name(n):
    n = re.sub(r"\s+", " ", str(n).strip().upper())
    if n in ALIASES:
        return ALIASES[n]
    n = re.sub(r"^CNX ", "NIFTY ", n)
    return ALIASES.get(n, n)


def parse(text, day):
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.strip().lower() for c in df.columns]
    ncol = next(c for c in df.columns if "index name" in c)
    ccol = next(c for c in df.columns if "closing" in c)
    out = pd.DataFrame({"index": df[ncol].map(clean_name),
                        "close": pd.to_numeric(df[ccol].astype(str).str.replace(",", ""), errors="coerce")})
    out["date"] = pd.Timestamp(day)
    return out.dropna()


def fetch_day(day, session):
    d = day.strftime("%d%m%Y")
    for u in URLS:
        try:
            r = session.get(u.format(d=d), headers=C.HTTP_HEADERS, timeout=30)
        except Exception:
            continue
        if r.status_code == 200 and "Index Name" in r.text[:300]:
            return parse(r.text, day)
        if r.status_code == 404:
            continue
    return None  # holiday / not published / blocked


def update(log=print):
    """Return the full price table (index, date, close), fetching only missing weekdays."""
    path = C.OUT / OUT_FILE
    have = pd.read_csv(path, parse_dates=["date"]) if path.exists() else pd.DataFrame(columns=["index", "date", "close"])
    start = pd.Timestamp(C.HISTORY_START)
    done = set(have.date.dt.normalize()) if len(have) else set()
    tried_file = C.CACHE / "nse_price_tried.txt"
    tried = set(pd.to_datetime(tried_file.read_text().split())) if tried_file.exists() else set()
    days = [d for d in pd.bdate_range(start, pd.Timestamp(dt.date.today()))
            if d not in done and (d not in tried or d > pd.Timestamp(dt.date.today()) - pd.Timedelta(days=10))]
    log(f"  NSE index prices: {len(done):,} days on file, fetching {len(days):,} more")
    frames, misses = [], []
    s = requests.Session()
    with ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(fetch_day, d, s): d for d in days}
        for n, f in enumerate(as_completed(futs), 1):
            res = f.result()
            (frames.append(res) if res is not None else misses.append(futs[f]))
            if n % 500 == 0:
                log(f"    {n:,}/{len(days):,} days checked | got {len(frames):,}")
    if days and not frames and len(days) > 20:
        log("  WARNING: no NSE index files could be downloaded (blocked or moved); price history not updated")
    C.CACHE.mkdir(exist_ok=True)
    tried_file.write_text("\n".join(str(d.date()) for d in sorted(tried | set(misses))))
    allp = pd.concat([have] + frames, ignore_index=True) if frames else have
    if len(allp):
        allp = allp.drop_duplicates(["index", "date"], keep="last").sort_values(["index", "date"])
        allp.to_csv(path, index=False, compression="gzip")
        log(f"  NSE index prices: {allp['index'].nunique():,} indices, {allp.date.min().date()} → {allp.date.max().date()}")
    return allp
