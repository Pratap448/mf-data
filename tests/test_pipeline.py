"""Offline test: fakes AMFI / NSE responses with synthetic data and runs the full build.
Run: python -m tests.test_pipeline
"""
import datetime as dt, json, shutil, tempfile
from pathlib import Path
import numpy as np, pandas as pd
from mfrepo import config as C, amfi, indices, build

rng = np.random.default_rng(7)
TODAY = dt.date.today()
SCHEMES = [  # code, name, category, drift
    (100, "Alpha Large Cap Fund - Regular Plan - Growth", "Equity Scheme - Large Cap Fund", 0.13),
    (101, "Alpha Large Cap Fund - Direct Plan - Growth", "Equity Scheme - Large Cap Fund", 0.14),
    (102, "Beta Large Cap Fund - Regular Plan - Growth", "Equity Scheme - Large Cap Fund", 0.10),
    (103, "Gamma Large Cap Fund - Regular Plan - IDCW", "Equity Scheme - Large Cap Fund", 0.10),
    (200, "Alpha Small Cap Fund - Regular Plan - Growth", "Equity Scheme - Small Cap Fund", 0.18),
    (201, "Beta Small Cap Fund - Regular Plan - Growth", "Equity Scheme - Small Cap Fund", 0.15),
    (300, "Alpha Nifty 50 Index Fund - Regular Plan - Growth", "Other Scheme - Index Funds", 0.12),
]
DATES = pd.bdate_range(TODAY - dt.timedelta(days=365 * 7), TODAY)
PATH = {}
for code, _, _, mu in SCHEMES:
    r = rng.normal(mu / 252, 0.15 / np.sqrt(252), len(DATES))
    PATH[code] = pd.Series(10 * np.exp(np.cumsum(r)), index=DATES)
TRI = {n: pd.Series(1000 * np.exp(np.cumsum(rng.normal(0.12 / 252, 0.14 / np.sqrt(252), len(DATES)))), index=DATES)
       for n in ["NIFTY 50", "NIFTY SMALLCAP 250"]}


def fake_get(url):
    if "NAVAll" in url:
        lines = ["Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date", ""]
        for cat in sorted({c for _, _, c, _ in SCHEMES}):
            lines += [f"Open Ended Schemes({cat})", "", "Alpha Mutual Fund", ""]
            for code, name, c, _ in SCHEMES:
                if c == cat:
                    lines.append(f"{code};INF000{code};-;{name};{PATH[code].iloc[-1]:.4f};{DATES[-1]:%d-%b-%Y}")
        return "\n".join(lines)
    q = dict(p.split("=") for p in url.split("?")[1].split("&"))
    f, t = pd.to_datetime(q["frmdt"]), pd.to_datetime(q["todt"])
    out = ["Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Net Asset Value;Repurchase Price;Sale Price;Date"]
    for code, name, _, _ in SCHEMES:
        s = PATH[code][(PATH[code].index >= f) & (PATH[code].index <= t)]
        out += [f"{code};{name};INF000{code};;{v:.4f};;;{d:%d-%b-%Y}" for d, v in s.items()]
    return "\n".join(out)


def fake_year(s, name, start, end):
    x = TRI[name]
    x = x[(x.index >= pd.Timestamp(start)) & (x.index <= pd.Timestamp(end))]
    return pd.DataFrame({"date": x.index, "tri": x.values})


def run():
    tmp = Path(tempfile.mkdtemp())
    for k in ("CACHE", "OUT"):
        setattr(C, k, tmp / k.lower())
    amfi._get = fake_get
    amfi.time.sleep = lambda *_: None
    indices._fetch_year = fake_year
    indices._session = lambda: None
    indices.time.sleep = lambda *_: None
    build.main()
    fm = pd.read_csv(C.OUT / "fund_metrics.csv")
    assert set(fm.amfi_code) == {100, 101, 102, 200, 201, 300}, fm.amfi_code.tolist()   # IDCW excluded
    lc = fm[fm.peer_group == "Equity Scheme - Large Cap Fund | Regular"]
    assert len(lc) == 2 and lc.rank_3y.isna().all()          # Regular-only peers; <MIN_PEERS so no rank
    C.MIN_PEERS = 1; build.main(); fm = pd.read_csv(C.OUT / "fund_metrics.csv")
    lc = fm[fm.peer_group == "Equity Scheme - Large Cap Fund | Regular"]
    assert sorted(lc.quartile_3y) == [1, 3], lc.quartile_3y.tolist()
    assert fm.loc[fm.amfi_code == 300, "peer_group"].iloc[0].startswith("Other Scheme - Index Funds | NIFTY 50")
    r = fm.set_index("amfi_code").loc[100]
    exp3 = ((PATH[100].asof(pd.Timestamp(r.as_of)) / PATH[100].asof(pd.Timestamp(r.as_of) - pd.DateOffset(years=3))) ** (1 / 3) - 1) * 100
    assert abs(r.ret_3y - exp3) < 0.05, (r.ret_3y, exp3)
    for c in ["roll3y_avg", "sd_3y", "sharpe_3y", "alpha_3y", "up_capture", "bm_ret_3y", "quartile_roll3y"]:
        assert pd.notna(r[c]), c
    # incremental second run reuses cache
    build.main()
    print("\nTEST PASSED")
    print(fm[["amfi_code", "peer_group", "ret_1y", "ret_3y", "roll3y_avg", "sharpe_3y", "alpha_3y",
              "capture_ratio", "rank_3y", "quartile_3y"]].to_string())
    shutil.rmtree(tmp)


if __name__ == "__main__":
    run()
