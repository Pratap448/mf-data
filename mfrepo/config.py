"""Settings for the MF data repository. Edit values here, not in the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data_cache"          # full daily history (not committed; kept in Actions cache)
OUT = ROOT / "data"                  # compact outputs (committed; read via raw GitHub links)
CONFIG = ROOT / "config"
MANUAL_TRI = ROOT / "manual" / "tri" # optional hand-placed TRI CSVs: Date,TRI

RF_RATE = 0.065            # annual risk-free rate for Sharpe/alpha (approx. 91-day T-bill); update as needed
HISTORY_START = "2010-01-01"  # NAV and benchmark history kept from this date
ROLL_WINDOW_YEARS = 3      # rolling-return window
ROLL_DATA_YEARS = 5        # rolling windows must sit inside the last 5 years; fund needs a 5-year record
RISK_MONTHS = 36
MIN_PEERS = 4             # rank/quartile shown only when the peer group has at least this many schemes           # months used for Std Dev / Sharpe / Beta / Alpha / Capture
NAV_CHUNK_DAYS = 90        # AMFI NAV-history request size
KEEP_GROUPS = None  # None = keep every category group (Equity, Debt, Hybrid, Solution Oriented, Other, close-ended)
KEEP_TYPES = None   # None = Open Ended, Close Ended and Interval Fund schemes
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# Benchmark series from index-tracking schemes: annual expense added back to NAV
BENCH_ER_ADDBACK = {"direct": 0.002, "etf": 0.001, "regular": 0.008, "commodity": 0.005}
