# MF Data Repository (SEBI categories, official data)

Refreshes every 15 days and publishes ready-made fund metrics so portfolio reviews need only the client CAS.

**Sources (official only):** AMFI (scheme master with SEBI category, daily NAV history), NSE Indices (benchmark TRI).
**Not used:** Morningstar or any rating site.

---

## 1. One-time setup on GitHub (about 10 minutes, no PC needed afterwards)

1. Create a free GitHub account (or use the firm's).
2. Click **New repository** and name it, e.g. `mf-data`.
   - Make it **Public**. Claude can read public file links only. It holds only public AMFI/NSE data and **no client data**.
3. Click **Add file → Upload files**, then drag in everything from this folder (keep the folder structure, including `.github/workflows/refresh.yml`).
4. Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**. Save.
5. Go to the **Actions** tab, open **Refresh MF data**, then click **Run workflow** for the first build.
   - The first run downloads 6 years of history and takes roughly 30–60 minutes. Later runs are quicker.
6. When it finishes, the `data/` folder contains the CSV files. Send Claude this link:
   `https://raw.githubusercontent.com/<your-user>/<repo>/main/data/`

After that it runs by itself at 03:00 IST on the 2nd and 16th of each month. You can also press **Run workflow** for an ad-hoc refresh.

### Alternative: run on your own PC

```
pip install -r requirements.txt
python -m mfrepo.build
```
Outputs go to `data/`. For Claude to read them, push to GitHub the same way.

---

## 2. Output files (`data/`)

| File | What it holds |
|---|---|
| `fund_metrics.csv` | **Main file.** One row per open-ended Growth scheme (Regular and Direct): SEBI category, peer group, benchmark, YTD/1Y/3Y/5Y returns, 3Y rolling average, Std Dev, Sharpe, Beta, Alpha, Up/Down capture, Capture ratio, benchmark returns, excess returns, rank/percentile/quartile (3Y and 3Y rolling), and category averages |
| `category_stats.csv` | Peer-group averages of every metric plus the number of schemes |
| `scheme_master.csv` | All open-ended schemes (all plans/options), with ISINs, used to match CAS ISINs |
| `benchmark_tri.csv` | Daily TRI of each benchmark, used for "same cash flows in benchmark" returns |
| `nav_month_end.csv.gz` | Month-end NAVs of all Growth schemes |
| `run_info.json` | As-of date, run time, methods used |

## 3. Methods

- **Peer group:** SEBI category × plan (Regular/Direct), Growth option only. Index funds and ETFs are grouped by the index they track.
- **Returns:** point-to-point NAV; CAGR for periods over 1 year; YTD from the last NAV of the previous year.
- **3Y rolling:** average of daily 3-year CAGRs with windows inside the last 5 years. Requires a 5-year record (the template rule).
- **Risk (36 monthly returns):**
  - Std Dev is annualised.
  - Sharpe = (annual return − risk-free) ÷ Std Dev, using `RF_RATE` in `mfrepo/config.py` (default 6.5%).
  - Beta and Jensen's alpha are measured against the benchmark TRI.
  - Capture uses geometric up-month and down-month returns. Capture ratio = up ÷ down; NA if the fund rose in down months.
- **Rank:** 1 = best. Quartile Q1 = top 25%. Shown only if the peer group has at least 4 schemes (`MIN_PEERS`).
- **Category average:** simple average of the peer group.

## 4. Things you may edit

- `config/benchmark_map.csv`: benchmark index per SEBI category (matched on text in the category name).
- `config/scheme_benchmark_overrides.csv`: per-scheme benchmark (e.g. a scheme whose SID benchmark differs).
- `mfrepo/config.py`: risk-free rate, look-back years, minimum peers.
- `manual/tri/<INDEX NAME>.csv`: if NSE Indices blocks a download, drop a CSV with columns `Date,TRI` here (e.g. `manual/tri/NIFTY 50.csv`).

## 5. Known limits (v1)

- **Hybrid benchmarks (CRISIL indices), global indices (S&P 500, MSCI) and gold/silver prices** are not on NSE Indices. These schemes get returns, Std Dev, Sharpe and peer ranks, but no benchmark-based alpha, beta or capture unless a manual TRI file is added.
- **Plan and option** are detected from scheme names (Direct, IDCW, Growth). Spot-check unusual names.
- **AMC portfolio holdings** (look-through, overlap, YTM, duration) and **expense ratios** are planned for v2.
- **The GitHub cache of daily history is cleared after 7 days unused,** so each fortnightly run may re-download the full history. This is slower but harmless.
- **NSE Indices endpoint:** the site's data endpoint is not an official API and may change. Failures are logged in the run, and the rest of the build still completes.

## 6. Test

`python -m tests.test_pipeline` runs the whole pipeline on synthetic data and checks the calculations.
