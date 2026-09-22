"""
config.py - Round 3 Central Configuration
Data Vortex A'26 | Team: Event Horizon

Single edit point for topic, keywords, sources, and detection thresholds.
All API credentials are read from environment variables — never hardcode secrets.
"""

import os
from datetime import datetime, timezone

TOPIC = "WhatsApp Privacy Policy 2021"
TOPIC_SLUG = "whatsapp_privacy_2021"

KEYWORDS = [
    "WhatsApp privacy policy",
    "WhatsApp new terms",
    "WhatsApp privacy update",
    "WhatsApp data sharing",
    "WhatsApp privacy",
    "delete WhatsApp",
    "leave WhatsApp",
    "WhatsApp alternatives",
    "WhatsApp ban",
    "WhatsApp January 2021",
]

KEYWORDS_ID = [
    "kebijakan privasi WhatsApp",
    "WhatsApp hapus",
    "privasi WhatsApp",
]

DATE_START = "2020-11-01"
DATE_END   = "2021-07-31"

GEOGRAPHY = {
    "countries": ["in", "id", "us", "gb"],
    "langs": ["en", "id"],
    "reddit_subreddits": ["privacy", "technology", "india", "Indonesia", "worldnews", "WhatsApp"],
}

SOURCES = {
    "gdelt":        True,
    "google_play":  True,
    "hn":           True,
    "reddit":       False,
    "kaggle":       False,
}

GOOGLE_PLAY_APP_ID = "com.whatsapp"
GOOGLE_PLAY_LANGS  = ["en", "id"]
GOOGLE_PLAY_COUNTRIES = ["in", "id", "us", "gb"]

REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = "DataVortex_R3_EventHorizon/1.0"

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

KAGGLE_DATASET_QUERY = "whatsapp privacy 2021"

SCHEDULER_INTERVAL_MINUTES = 30

SPIKE_ZSCORE_THRESHOLD     = 2.0
SHIFT_ZSCORE_THRESHOLD     = 1.5
ROLLING_WINDOW_HOURS       = 24
SENTIMENT_MAP              = {"Negative": 0.0, "Neutral": 0.5, "Positive": 1.0}

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
DATA_PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORTS_DIR   = os.path.join(BASE_DIR, "reports")
FIGURES_DIR   = os.path.join(REPORTS_DIR, "figures")
COLL_LOG_PATH = os.path.join(BASE_DIR, "data", "collection_log.csv")

MODEL_PATH = os.path.join(
    BASE_DIR, "..", "round2", "models", "sentiment_linear_svm.pkl"
)
