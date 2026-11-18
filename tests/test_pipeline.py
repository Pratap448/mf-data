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
    (104, "Alpha Large Cap Fund - Regular Plan - IDCW", "Equity Scheme - Large Cap Fund", 0.13),
    (200, "Alpha Small Cap Fund - Regular Plan - Growth", "Equity Scheme - Small Cap Fund", 0.18),
    (201, "Beta Small Cap Fund - Regular Plan - Growth", "Equity Scheme - Small Cap Fund", 0.15),
    (300, "Alpha Nifty 50 Index Fund - Regular Plan - Growth", "Other Scheme - Index Funds", 0.12),
    (301, "Alpha Nifty 100 Index Fund - Direct Plan - Growth", "Other Scheme - Index Funds", 0.125),
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


def fake_mfapi(code, start, end):
    if code not in PATH:
        return None
    x = PATH[code]
    x = x[(x.index >= pd.Timestamp(start)) & (x.index <= pd.Timestamp(end))]
    return pd.DataFrame({"amfi_code": code, "date": x.index, "nav": x.values})


def fake_year(s, name, start, end):
    x = TRI[name]
    x = x[(x.index >= pd.Timestamp(start)) & (x.index <= pd.Timestamp(end))]
    return pd.DataFrame({"date": x.index, "tri": x.values})


def run():
    tmp = Path(tempfile.mkdtemp())
    for k in ("CACHE", "OUT"):
        setattr(C, k, tmp / k.lower())
    C.FETCH_TER = C.FETCH_HOLDINGS = C.INCLUDE_SIF = False
    amfi._get = fake_get
    amfi.time.sleep = lambda *_: None
    amfi._mfapi_one = fake_mfapi
    amfi._full_names = lambda: {}
    amfi.official_plan_option = lambda m, log=print: m
    amfi.nav_fallback = lambda codes, s, e, log=print: pd.DataFrame(columns=["amfi_code", "date", "nav"])
    from mfrepo import nse_prices; nse_prices.update = lambda log=print: None
    indices._fetch_year = fake_year
    indices._session = lambda: None
    indices.time.sleep = lambda *_: None
    build.main()
    fm = pd.read_parquet(C.OUT / "fund_metrics.parquet")
    assert set(fm.amfi_code) == {100, 101, 102, 103, 104, 200, 201, 300, 301}, fm.amfi_code.tolist()
    a, b = fm.set_index("amfi_code").loc[100], fm.set_index("amfi_code").loc[104]
    assert a.ret_3y == b.ret_3y and b.metrics_basis.startswith("Growth option 100"), b.metrics_basis
    assert "payouts not added back" in fm.set_index("amfi_code").loc[103, "metrics_basis"]
    g = fm[fm.option == "Growth"]
    lc = g[g.peer_group == "Equity Scheme - Large Cap Fund | Regular"]
    assert len(lc) == 2 and lc.ret_3y_rank.isna().all()          # < MIN_PEERS -> no rank
    C.MIN_PEERS = 1
    build.main(offline=True)                                      # offline recompute from data/ only
    fm = pd.read_parquet(C.OUT / "fund_metrics.parquet")
    g = fm[fm.option == "Growth"]
    lc = g[g.peer_group == "Equity Scheme - Large Cap Fund | Regular"]
    assert sorted(lc.ret_3y_quartile) == [1, 3], lc.ret_3y_quartile.tolist()
    r = g.set_index("amfi_code").loc[100]
    exp3 = ((PATH[100].asof(pd.Timestamp(r.as_of)) / PATH[100].asof(pd.Timestamp(r.as_of) - pd.DateOffset(years=3))) ** (1 / 3) - 1) * 100
    assert abs(r.ret_3y - exp3) < 0.05, (r.ret_3y, exp3)
    for c in ["roll_avg_3y", "std_dev_3y", "sharpe_3y", "sortino_3y", "max_drawdown_3y", "alpha_3y", "beta_3y",
              "up_capture_3y", "information_ratio_3y", "cat_beta_3y", "bm_ret_3y", "catidx_ret_3y", "cy_2023",
              "sharpe_5y", "ret_3y_quartile", "cat_avg_ret_3y"]:
        assert c in r.index and pd.notna(r[c]), c
    # analytics on the stored data, any window
    from mfrepo.analytics import Repo, metrics, compare
    rp = Repo(tmp)
    rp.d = C.OUT
    nav = rp.nav(100)
    m = metrics(nav, "2021-04-01", "2024-03-31", bm=rp.benchmark_of(100), cat=rp.category_of(100))
    assert m["sharpe"] is not None and m["beta"] is not None and m["cat_beta"] is not None
    assert len(rp.nav(104)) == len(nav)                              # IDCW resolves to Growth sibling
    cmp = compare([100, 101, 102], "2Y", r=rp, with_peers=True)
    assert len(cmp) == 3 and "sharpe_rank" in cmp
    assert (C.OUT / "category_index.parquet").exists() and (C.OUT / "COLUMNS.md").exists()
    assert list((C.OUT / "nav").glob("nav_*.parquet"))
    print("\nTEST PASSED")
    print(g[["amfi_code", "peer_group", "ret_1y", "ret_3y", "roll_avg_3y", "sharpe_3y", "alpha_3y",
             "capture_ratio_3y", "ret_3y_rank", "ret_3y_quartile"]].to_string())
    print(f"columns in fund_metrics: {fm.shape[1]}")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    run()
