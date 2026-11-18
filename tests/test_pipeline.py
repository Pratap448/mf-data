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
    (202, "Gamma Small Cap Fund - Regular Plan - Growth", "Equity Scheme - Small Cap Fund", 0.16),  # mfapi has no data
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


MFAPI_MISSING = {202}


def fake_mfapi(code, start, end):
    if code not in PATH or code in MFAPI_MISSING:
        return None
    x = PATH[code]
    x = x[(x.index >= pd.Timestamp(start)) & (x.index <= pd.Timestamp(end))]
    return pd.DataFrame({"amfi_code": code, "date": x.index, "nav": x.values})


def fake_year(s, name, start, end):
    x = TRI[name]
    x = x[(x.index >= pd.Timestamp(start)) & (x.index <= pd.Timestamp(end))]
    return pd.DataFrame({"date": x.index, "tri": x.values})


def fake_sif(log=print):
    d = pd.bdate_range(TODAY - dt.timedelta(days=500), TODAY)
    m = pd.DataFrame({"amfi_code": [9000120, 9000121], "scheme_name": ["Altiva Equity Long-Short Fund - Direct Plan - Growth",
                      "Altiva Equity Long-Short Fund - Regular Plan - Growth"], "amfi_name": "Altiva Equity Long-Short Fund",
                      "amc": "Altiva SIF", "scheme_type": "SIF", "sebi_category": "SIF - Equity Long-Short",
                      "category_group": "SIF", "plan": ["Direct", "Regular"], "option": "Growth", "isin_growth": "X",
                      "isin_reinv": None, "latest_nav": 11.0, "nav_date": pd.Timestamp(TODAY), "option_source": "amfi"})
    n = pd.concat([pd.DataFrame({"amfi_code": c, "date": pd.to_datetime(d).astype("datetime64[us]"),   # real API dtype
                                 "nav": 10 * np.exp(np.cumsum(rng.normal(0.0004, 0.006, len(d))))}) for c in m.amfi_code])
    return m, n


def fake_ter(log=print):
    return pd.DataFrame({"Scheme_Name": ["Alpha Large Cap Fund", "Beta Small Cap Fund"], "TER_Date": pd.Timestamp(TODAY),
                         "R_TER": [1.9, 2.1], "D_TER": [0.7, 0.9], "R_BER": [1.5, 1.7], "D_BER": [0.4, 0.6],
                         "R_BrokerageCost": 0.03, "D_BrokerageCost": 0.03, "R_TransactionCost": 0.0,
                         "D_TransactionCost": 0.0, "R_StatutoryLevies": 0.35, "D_StatutoryLevies": 0.12})


def make_portfolio(path):
    rows = [["Alpha Mutual Fund"], ["Portfolio of Alpha Large Cap Fund as on 31-Oct-2026"],
            ["Name of the Instrument", "ISIN", "Industry / Rating", "Quantity", "Market Value", "% to Net Assets", "Yield"],
            ["Equity & Equity related"], ["HDFC Bank Limited", "INE040A01034", "Banks", "10", "50", "9.5", None],
            ["Infosys Limited", "INE009A01021", "IT - Software", "5", "30", "5.0", None],
            ["Debt Instruments"], ["7.18% GOI 2033", "IN0020230085", "SOVEREIGN", "1", "10", "20.0", "6.85"],
            ["Bajaj Finance NCD", "INE296A07SR6", "CRISIL AAA", "1", "10", "60.0", "7.4"],
            ["TREPS", None, None, None, "5", "5.0", None], ["Net Receivables", None, None, None, "0.5", "0.5", None],
            ["Grand Total", None, None, None, "100", "100", None]]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def run():
    tmp = Path(tempfile.mkdtemp())
    for k in ("CACHE", "OUT"):
        setattr(C, k, tmp / k.lower())
    # temp project root with the real manual/ files + a dropped AMC portfolio (mirrors the live repo layout)
    root = tmp / "root"
    shutil.copytree(C.ROOT / "manual", root / "manual")
    shutil.copytree(C.ROOT / "config", root / "config")
    (root / "manual" / "portfolios" / "Alpha Mutual Fund").mkdir(parents=True, exist_ok=True)
    make_portfolio(root / "manual" / "portfolios" / "Alpha Mutual Fund" / "alpha_oct2026.xlsx")
    C.ROOT, C.CONFIG, C.MANUAL_TRI = root, root / "config", root / "manual" / "tri"
    C.INCLUDE_SIF = C.FETCH_TER = C.FETCH_HOLDINGS = True
    amfi._get = fake_get
    amfi.time.sleep = lambda *_: None
    amfi._mfapi_one = fake_mfapi
    amfi._full_names = lambda: {}
    amfi.official_plan_option = lambda m, log=print: m
    # the empty fallback frame (object dtypes) is exactly what broke the live run
    amfi.nav_fallback = lambda codes, s, e, log=print: pd.DataFrame(columns=["amfi_code", "date", "nav"])
    amfi.sif_data = fake_sif
    amfi.ter_latest = fake_ter
    from mfrepo import nse_prices, holdings
    nse_prices.update = lambda log=print: None
    holdings.download_amc = lambda row, target, s, outdir, log: ({"amc": row.amc, "page": row.page_url,
                                                                 "links_found": 0, "files": 0, "status": "test"}, [])
    holdings.requests.get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline test"))
    indices._fetch_year = fake_year
    indices._session = lambda: None
    indices.time.sleep = lambda *_: None
    build.main()
    info = json.loads((C.OUT / "run_info.json").read_text())
    assert all(str(v).startswith("ok") for v in info["status"].values()), info["status"]
    fm = pd.read_parquet(C.OUT / "fund_metrics.parquet")
    assert {100, 101, 102, 103, 104, 200, 201, 300, 301, 9000120, 9000121} <= set(fm.amfi_code), sorted(fm.amfi_code)
    a, b = fm.set_index("amfi_code").loc[100], fm.set_index("amfi_code").loc[104]
    assert a.ret_3y == b.ret_3y and b.metrics_basis.startswith("Growth option 100"), b.metrics_basis
    assert "payouts not added back" in fm.set_index("amfi_code").loc[103, "metrics_basis"]
    assert abs(fm.set_index("amfi_code").loc[101, "ter_total"] - 0.7) < 1e-9          # TER by plan
    sif = fm[fm.amfi_code == 9000120].iloc[0]
    assert sif.peer_group.startswith("SIF") and pd.notna(sif.ret_1y)                    # SIF metrics
    hs = pd.read_csv(C.OUT / "holdings_summary.csv")
    r0 = hs[hs.scheme_title.str.contains("Alpha Large Cap")].iloc[0]
    assert abs(r0.equity_gross_pct - 14.5) < 1e-6 and abs(r0.aaa_sov_pct_of_debt - 100) < 1e-6, r0.to_dict()
    assert r0.amfi_base == "Alpha Large Cap Fund", r0.amfi_base                         # matched to AMFI
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
    from mfrepo.analytics import Repo, metrics, compare
    rp = Repo(tmp)
    rp.d = C.OUT
    nav = rp.nav(100)
    m = metrics(nav, "2021-04-01", "2024-03-31", bm=rp.benchmark_of(100), cat=rp.category_of(100))
    assert m["sharpe"] is not None and m["beta"] is not None and m["cat_beta"] is not None
    assert len(rp.nav(104)) == len(nav)
    cmp = compare([100, 101, 102], "2Y", r=rp, with_peers=True)
    assert len(cmp) == 3 and "sharpe_rank" in cmp
    print("\nTEST PASSED  (status: " + ", ".join(f"{k}={v}" for k, v in info["status"].items()) + ")")
    print(f"columns in fund_metrics: {fm.shape[1]} | schemes: {len(fm)}")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    run()
