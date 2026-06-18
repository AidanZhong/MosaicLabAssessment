# Signal 1
GWP_UNDERPERFORMANCE_THRESHOLD = 0.60   # flag if actual/plan below this
MIN_WEEKS_BELOW_THRESHOLD      = 9     # must breach threshold in at least this many of 12 weeks

# Signal 2: Cyber hit rate collapse
HIT_RATE_DROP_THRESHOLD        = 0.10   # flag if (weeks 1-8 avg) minus (weeks 9-12 avg) exceeds this

# Signal 3: Environmental loss ratio deterioration
LOSS_RATIO_TARGET              = 0.60   # healthy ceiling, used across all signals
LOSS_RATIO_MIN_RISE            = 0.10   # flag if week-12 LR exceeds week-1 LR by at least this

# Signal 4: Political Violence outperformance
MIN_WEEKS_ABOVE_PLAN           = 8      # must beat plan in at least this many of 12 weeks

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

LOSS_INDICATOR_FILE = DATA_DIR / "case4_loss_indicators.csv"
PIPLINE_FILE = DATA_DIR / "case4_pipeline.csv"
WEEKLY_PREMIUM_FILE = DATA_DIR / "case4_weekly_premium.csv"
WEEKLY_SUBMISSION_FILE = DATA_DIR / "case4_weekly_submissions.csv"