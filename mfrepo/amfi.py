"""AMFI downloads: scheme master (with SEBI category) and daily NAV history."""
import io, re, time, datetime as dt
import pandas as pd, requests
from . import config as C

NAVALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
NAVALL_URLS = [NAVALL_URL, "https://www.amfiindia.com/spages/NAVAll.txt"]
HIST_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={f}&todt={t}"
CAT_RE = re.compile(r"^(Open[\s-]*Ended|Close[\s-]*Ended|Interval[\s-]*Funds?)\s*Schemes?\s*\((.+)\)\s*$", re.I)


def _kind(raw):
    r = raw.lower().replace("-", " ")
    return "Open Ended" if r.startswith("open") else "Close Ended" if r.startswith("close") else "Interval Fund"


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
    if any(k in n for k in ("idcw", "dividend", "payout", "reinvest", "bonus", "income distribution")):
        opt = "IDCW/Other"
    elif "growth" in n or "gr " in n or n.endswith(" gr") or "cumulative" in n:
        opt = "Growth"
    else:
        opt = "Unknown"
    return plan, opt


def parse_navall(text):
    """NAVAll.txt -> one row per scheme with SEBI category taken from the section headers.
    Columns are located from the 'Scheme Code;...' header, so added/reordered columns are handled."""
    rows, cat, kind, amc = [], None, None, None
    col = dict(code=0, isin_g=1, isin_r=2, name=3, nav=4, date=-1, plan=None, option=None)
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = CAT_RE.match(s)
        if m:
            kind, cat = _kind(m.group(1)), m.group(2).strip()
            continue
        parts = [p.strip() for p in s.split(";")]
        low = [p.lower() for p in parts]
        if low[0].startswith("scheme code"):
            for j, h in enumerate(low):
                if "growth" in h and "isin" in h: col["isin_g"] = j
                elif "reinvest" in h and "isin" in h: col["isin_r"] = j
                elif h.startswith("scheme name"): col["name"] = j
                elif "net asset value" in h or h == "nav": col["nav"] = j
                elif h == "date" or h.endswith(" date"): col["date"] = j
                elif "plan" in h and "isin" not in h: col["plan"] = j
                elif "option" in h and "isin" not in h: col["option"] = j
            continue
        if len(parts) >= 6 and parts[0].isdigit():
            g = lambda k: parts[col[k]] if col[k] is not None and col[k] < len(parts) else ""
            name = g("name")
            label = " ".join(x for x in (name, g("plan"), g("option")) if x)
            plan, opt = _plan_option(label)
            isin_g, isin_r = g("isin_g"), g("isin_r")
            rows.append(dict(amfi_code=int(parts[0]), isin_growth=isin_g if isin_g not in ("-", "") else None,
                             isin_reinv=isin_r if isin_r not in ("-", "") else None, scheme_name=name,
                             amc=amc, scheme_type=kind, sebi_category=cat,
                             category_group=cat.split(" - ")[0].strip() if cat else None,
                             plan=plan, option=opt,
                             latest_nav=pd.to_numeric(g("nav").replace(",", ""), errors="coerce"),
                             nav_date=pd.to_datetime(g("date"), format="%d-%b-%Y", errors="coerce")))
        elif len(parts) == 1 and not low[0].startswith("scheme code"):
            amc = s  # AMC name lines sit between category header and schemes
    return pd.DataFrame(rows)


MFAPI_LIST = "https://api.mfapi.in/mf"


def _full_names():
    """Full scheme names (with plan/option) from mfapi.in's scheme list, keyed by AMFI code.
    AMFI's NAVAll.txt now shows only the base fund name, so plan/option is read from these."""
    try:
        r = requests.get(MFAPI_LIST, headers=C.HTTP_HEADERS, timeout=120)
        r.raise_for_status()
        return {int(x["schemeCode"]): x["schemeName"].strip() for x in r.json() if str(x.get("schemeCode", "")).isdigit()}
    except Exception as e:
        print(f"  WARNING: mfapi.in scheme list unavailable ({e}); plan/option from AMFI names only")
        return {}


def _looks_like_navall(text):
    head = text[:3000].lower()
    return "scheme code" in head and "<html" not in head


def scheme_master():
    """Download NAVAll.txt (tries each AMFI address) and keep open-ended schemes."""
    text, problems = None, []
    for url in NAVALL_URLS:
        try:
            t = _get(url)
        except Exception as e:
            problems.append(f"{url}: {e}")
            continue
        if _looks_like_navall(t):
            text = t
            break
        problems.append(f"{url}: unexpected content ({len(t):,} chars). Starts with: {t[:300]!r}")
    if text is None:
        raise RuntimeError("AMFI scheme master not usable (likely blocked or format changed):\n  "
                           + "\n  ".join(problems))
    df = parse_navall(text)
    if df.empty:
        raise RuntimeError("NAVAll.txt downloaded but no scheme rows parsed. First 500 chars:\n"
                           + repr(text[:500]))
    head = [l for l in text.splitlines() if l.strip()][:1]
    sample = next((l for l in text.splitlines() if l.split(";")[0].strip().isdigit()), "")
    print(f"  NAVAll header: {head[0][:250] if head else ''!r}")
    print(f"  NAVAll sample: {sample[:250]!r}")
    full = _full_names()
    if full:
        df["amfi_name"] = df["scheme_name"]
        df["scheme_name"] = [full.get(c, n) for c, n in zip(df.amfi_code, df.scheme_name)]
        po = [_plan_option(n) for n in df.scheme_name]
        df["plan"], df["option"] = [p for p, _ in po], [o for _, o in po]
    # When the name is silent: payout+reinvest ISIN pair => IDCW; single ISIN => Growth (flagged)
    df["option_source"] = "name"
    unk = (df.option == "Unknown")
    df.loc[unk & df.isin_reinv.notna(), ["option", "option_source"]] = ["IDCW/Other", "isin"]
    unk = (df.option == "Unknown")
    df.loc[unk & df.isin_growth.notna(), ["option", "option_source"]] = ["Growth", "isin"]
    print(f"  AMFI master: {len(df):,} rows; scheme types: {df.scheme_type.value_counts(dropna=False).to_dict()}")
    print(f"  plan: {df.plan.value_counts().to_dict()} | option: {df.option.value_counts().to_dict()}")
    keep = df[(df.scheme_type == "Open Ended") & df.category_group.isin(C.KEEP_GROUPS)]
    if keep.empty:
        raise RuntimeError("No open-ended schemes in kept groups. Category groups seen: "
                           + str(df.category_group.value_counts().head(15).to_dict()))
    return keep.reset_index(drop=True)


HIST_URLS = [HIST_URL, "https://www.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={f}&todt={t}"]


def parse_history(text, keep_codes=None):
    """NAV history report -> (amfi_code, date, nav). Columns are found from the header line,
    so extra/reordered columns don't break it; falls back to the classic 8-column layout."""
    i_code, i_nav, i_date = 0, 4, 7
    out = []
    for line in text.splitlines():
        p = [x.strip() for x in line.split(";")]
        low = [x.lower() for x in p]
        if low and low[0].startswith("scheme code"):
            for j, h in enumerate(low):
                if h.startswith("scheme code"): i_code = j
                elif "net asset value" in h or h == "nav": i_nav = j
                elif h == "date" or h.startswith("nav date") or h.endswith(" date"): i_date = j
            continue
        if len(p) > max(i_code, i_nav, i_date) and p[i_code].isdigit():
            code = int(p[i_code])
            if keep_codes is not None and code not in keep_codes:
                continue
            out.append((code, p[i_nav], p[i_date]))
    if not out:
        return pd.DataFrame(columns=["amfi_code", "date", "nav"])
    df = pd.DataFrame(out, columns=["amfi_code", "nav", "date"])
    df["nav"] = pd.to_numeric(df["nav"].str.replace(",", ""), errors="coerce")
    d = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    if d.isna().mean() > 0.5:  # other date styles, e.g. 13-11-2026 or 2026-11-13
        d = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["date"] = d
    return df.dropna()[["amfi_code", "date", "nav"]]


def _fetch_hist(d, e, keep_codes, log):
    """One date window; tries each AMFI address. Logs what came back if nothing parses."""
    f, t = d.strftime("%d-%b-%Y"), e.strftime("%d-%b-%Y")
    notes = []
    for u in HIST_URLS:
        url = u.format(f=f, t=t)
        try:
            text = _get(url)
        except Exception as ex:
            notes.append(f"{url} -> error {ex}")
            continue
        part = parse_history(text, keep_codes)
        if len(part):
            return part
        all_rows = len(parse_history(text))
        notes.append(f"{url} -> {len(text):,} chars, {all_rows:,} rows before scheme filter; "
                     f"starts: {text[:400]!r}")
    for n in notes:
        log("    DIAG " + n)
    return pd.DataFrame(columns=["amfi_code", "date", "nav"])


MFAPI_URL = "https://api.mfapi.in/mf/{code}?startDate={s}&endDate={e}"
MFAPI_WORKERS = 8


def _mfapi_one(code, start, end):
    """Full NAV history for one scheme from mfapi.in (a mirror of AMFI's NAV data)."""
    url = MFAPI_URL.format(code=code, s=start.isoformat(), e=end.isoformat())
    for i in range(4):
        try:
            r = requests.get(url, headers=C.HTTP_HEADERS, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json().get("data") or []
            if not data:
                return None
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
            df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
            df = df.dropna()
            df = df[(df.date >= pd.Timestamp(start)) & (df.date <= pd.Timestamp(end)) & (df.nav > 0)]
            return df.assign(amfi_code=int(code))[["amfi_code", "date", "nav"]]
        except Exception:
            if i == 3:
                raise
            time.sleep(3 * (i + 1))


def nav_history(start, end, keep_codes, log=print):
    """Daily NAVs for the given schemes, via mfapi.in (AMFI's own history download now
    returns a web form instead of data, so it can't be automated)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    codes = sorted(keep_codes)
    log(f"  Fetching NAV history for {len(codes):,} schemes from mfapi.in …")
    frames, failed, empty = [], [], 0
    with ThreadPoolExecutor(MFAPI_WORKERS) as ex:
        futs = {ex.submit(_mfapi_one, c, start, end): c for c in codes}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                df = f.result()
                if df is None or not len(df):
                    empty += 1
                else:
                    frames.append(df)
            except Exception as e:
                failed.append(futs[f])
            if n % 500 == 0 or n == len(codes):
                log(f"    {n:,}/{len(codes):,} done | with data {len(frames):,} | empty {empty:,} | failed {len(failed):,}")
    if failed:
        log(f"  WARNING: {len(failed)} schemes failed to download, e.g. {failed[:10]}")
    if not frames:
        raise RuntimeError("mfapi.in returned no NAV data for any scheme.")
    out = pd.concat(frames, ignore_index=True)
    log(f"  NAV rows: {len(out):,} for {out.amfi_code.nunique():,} schemes")
    return out
