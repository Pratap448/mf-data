"""AMFI downloads: scheme master (with SEBI category) and daily NAV history."""
import io, re, time, datetime as dt
import pandas as pd, requests
from . import config as C

NAVALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
HIST_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={f}&todt={t}"
CAT_RE = re.compile(r"^(Open Ended|Close Ended|Interval Fund) Schemes?\s*\((.+)\)\s*$", re.I)


def _get(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, headers=C.HTTP_HEADERS, timeout=120)
            r.raise_for_status()
            return r.text
        except Exception as e:  # network hiccups: back off and retry
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def _plan_option(name):
    n = name.lower()
    plan = "Direct" if "direct" in n else "Regular"
    if any(k in n for k in ("idcw", "dividend", "payout", "reinvest", "bonus")):
        opt = "IDCW/Other"
    elif "growth" in n or "gr " in n or n.endswith(" gr"):
        opt = "Growth"
    else:
        opt = "Unknown"
    return plan, opt


def parse_navall(text):
    """NAVAll.txt -> one row per scheme with SEBI category taken from the section headers."""
    rows, cat, kind, amc = [], None, None, None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = CAT_RE.match(s)
        if m:
            kind, cat = m.group(1).title(), m.group(2).strip()
            continue
        parts = s.split(";")
        if len(parts) == 6 and parts[0].strip().isdigit():
            code, isin_g, isin_r, name, nav, date = [p.strip() for p in parts]
            plan, opt = _plan_option(name)
            rows.append(dict(amfi_code=int(code), isin_growth=isin_g if isin_g not in ("-", "") else None,
                             isin_reinv=isin_r if isin_r not in ("-", "") else None, scheme_name=name,
                             amc=amc, scheme_type=kind, sebi_category=cat,
                             category_group=cat.split(" - ")[0].strip() if cat else None,
                             plan=plan, option=opt, latest_nav=pd.to_numeric(nav, errors="coerce"),
                             nav_date=pd.to_datetime(date, format="%d-%b-%Y", errors="coerce")))
        elif len(parts) == 1 and not s.lower().startswith("scheme code"):
            amc = s  # AMC name lines sit between category header and schemes
    return pd.DataFrame(rows)


def scheme_master():
    df = parse_navall(_get(NAVALL_URL))
    df = df[(df.scheme_type == "Open Ended") & df.category_group.isin(C.KEEP_GROUPS)]
    return df.reset_index(drop=True)


def parse_history(text, keep_codes=None):
    out = []
    for line in text.splitlines():
        p = line.split(";")
        if len(p) >= 8 and p[0].strip().isdigit():
            code = int(p[0])
            if keep_codes is not None and code not in keep_codes:
                continue
            out.append((code, p[4].strip(), p[7].strip()))
    if not out:
        return pd.DataFrame(columns=["amfi_code", "date", "nav"])
    df = pd.DataFrame(out, columns=["amfi_code", "nav", "date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    return df.dropna()[["amfi_code", "date", "nav"]]


def nav_history(start, end, keep_codes, log=print):
    frames, d = [], start
    while d <= end:
        e = min(d + dt.timedelta(days=C.NAV_CHUNK_DAYS - 1), end)
        url = HIST_URL.format(f=d.strftime("%d-%b-%Y"), t=e.strftime("%d-%b-%Y"))
        part = parse_history(_get(url), keep_codes)
        log(f"  NAV {d} → {e}: {len(part):,} rows")
        frames.append(part)
        d = e + dt.timedelta(days=1)
        time.sleep(1)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["amfi_code", "date", "nav"])
