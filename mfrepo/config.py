"""Settings for the MF data repository. Edit values here (or the CSVs in config/), not in the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data_cache"          # working files (not committed; kept in the Actions cache)
OUT = ROOT / "data"                  # outputs committed to the repo
CONFIG = ROOT / "config"
MANUAL_TRI = ROOT / "manual" / "tri" # optional hand-placed index CSVs: Date,TRI

# ---- history & measurement
HISTORY_START = "2010-01-01"   # NAV and benchmark history kept from this date
RF_RATE = 0.065                # annual risk-free rate for Sharpe / Sortino / alpha / Treynor
RISK_FREQ = "M"                # return frequency for risk ratios in the standard snapshot: M, W or D
SNAPSHOT_WINDOWS = [1, 3, 5, 7, 10]          # years: risk / relative measures in fund_metrics
ROLLING_WINDOWS = ["1Y", "3Y", "5Y"]         # rolling-return stats in fund_metrics
ROLLING_LOOKBACK_YEARS = 10                  # rolling windows taken from the last N years
CALENDAR_YEARS = 10                          # calendar-year returns in fund_metrics
MIN_PEERS = 4                  # rank / quartile only when the peer group has at least this many schemes
STALE_DAYS = 10                # scheme ignored if its last NAV is older than this vs the as-of date

# kept for older code paths
ROLL_WINDOW_YEARS = 3
ROLL_DATA_YEARS = 5
RISK_MONTHS = 36
NAV_CHUNK_DAYS = 90

# ---- universe
KEEP_GROUPS = None   # None = keep every category group
KEEP_TYPES = None    # None = Open Ended, Close Ended and Interval Fund schemes
INCLUDE_SIF = True   # Specialised Investment Funds from AMFI
FETCH_TER = True     # Total Expense Ratio from AMFI
FETCH_HOLDINGS = True  # AMC monthly portfolios (config/amc_portfolio_sources.csv + manual/portfolios/)

# ---- web
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
# AMFI large/mid/small cap list (half-yearly). Put the file in manual/mcap/ if the URL changes.
MCAP_URLS = []

# Benchmark series from index-tracking schemes: annual expense added back to NAV
BENCH_ER_ADDBACK = {"direct": 0.002, "etf": 0.001, "regular": 0.008, "commodity": 0.005}
