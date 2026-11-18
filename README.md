# mf-data — Indian mutual fund data store & analytics

A GitHub Actions job refreshes everything on the 2nd and 16th of each month (03:00 IST), or on demand
(Actions → Refresh MF data → Run workflow). The repo is a **data store**; every ratio for any period is
computed from it by `mfrepo/analytics.py`, so new measures never require changing the data pipeline.

## What is stored (`data/`)

| File | Content |
|---|---|
| `nav/nav_YYYY.parquet` | Daily NAV of every scheme from 2010 (MF from AMFI via mfapi.in, AMFI fallback; SIF from AMFI) |
| `scheme_master.csv` | Every scheme: AMC, SEBI category, plan, option, ISINs, peer group, benchmark, `nav_source_code` (IDCW → Growth sibling), TER |
| `benchmark_tri.csv.gz` | Daily benchmark levels: official NSE TRI (2010+) extended by index funds; composites for debt/hybrid; gold/silver |
| `benchmark_sources.csv` | How each benchmark series was built (audit) |
| `index_price.csv.gz` | NSE price indices (daily file, 2012+) |
| `category_index.parquet` | Daily equal-weighted index of each peer group (category average path) |
| `fund_metrics.parquet` / `.csv.gz` | Ready snapshot: trailing & calendar returns, risk / relative / category measures for 1, 3, 5, 7, 10 years, rolling stats, peer ranks. See `COLUMNS.md` |
| `category_stats.parquet` / `.csv` | Category average & median of every measure |
| `ter.csv` | Latest TER (total, base, brokerage, transaction, statutory) from AMFI |
| `holdings/holdings_YYYY-MM.parquet` | Security-level portfolios from AMC monthly disclosures |
| `holdings_summary.csv` | Per scheme: equity gross/net, debt, cash, large/mid/small, YTM, AAA+SOV %, credit mix, top-10 weight |
| `holdings_coverage.csv` | Which AMCs were downloaded / parsed / matched this month |
| `mcap_classification.csv` | AMFI large / mid / small cap list |
| `run_info.json` | As-of date, counts, status of each step |

## Analytics for any period

```python
from mfrepo.analytics import Repo, metrics, compare, rolling_returns, mirror_xirr, xirr, sip_returns
r = Repo("path/to/mf-data")
nav, bm, cat = r.nav(118668), r.benchmark_of(118668), r.category_of(118668)
metrics(nav, "2019-04-01", "2024-03-31", bm=bm, cat=cat)        # ~140 measures for that exact window
metrics(nav, "3Y", freq="D")                                     # last 3 years on daily returns
compare([118668, 120505, 119551], "5Y", r=r, with_peers=True)   # side by side + rank within category
rolling_returns(nav, "3Y", "2015-01-01", bm=bm)                  # rolling series + % beating benchmark
mirror_xirr(client_cashflows, bm, "2026-11-17")                  # benchmark XIRR on the client's cash flows
```

Measures: point-to-point / CAGR, trailing (1M…10Y, SI), calendar & financial-year returns, rolling
returns (avg, median, min, max, % positive, % above thresholds, % beating benchmark), SIP returns,
XIRR, benchmark / category XIRR on the same cash flows, annualised return, standard deviation, downside
deviation, Sharpe, Sortino, Calmar, Omega, Treynor, M², max drawdown (with dates, recovery, longest
under water), Ulcer index, VaR / CVaR, skewness, kurtosis, beta, Jensen's alpha, R², correlation,
tracking error, information ratio, up / down capture (geometric & arithmetic), capture ratio, batting
averages, excess return — each against the benchmark and against the category index; ranks, percentiles
and quartiles within the peer group. Holdings: allocation, net equity, market-cap split, YTM, AAA+SOV,
credit mix, concentration, overlap between any two schemes.

## Configuration (edit on GitHub, no code changes)

| File | Purpose |
|---|---|
| `mfrepo/config.py` | Risk-free rate, history start, snapshot windows, feature switches |
| `config/benchmark_map.csv` | SEBI category → benchmark |
| `config/theme_map.csv` | Sectoral / thematic fund → theme → benchmark |
| `config/composite_benchmarks.csv` | Debt / hybrid composite benchmarks |
| `config/scheme_benchmark_overrides.csv` | Benchmark for a specific AMFI code |
| `config/amc_portfolio_sources.csv` | AMC portfolio disclosure pages (from AMFI) |
| `manual/official_*.csv` | Official NSE index history (one-time) |
| `manual/portfolios/` | Drop any AMC portfolio Excel/ZIP here; it is parsed on the next run |
| `manual/mcap/` | AMFI market-cap list if the automatic download fails |
