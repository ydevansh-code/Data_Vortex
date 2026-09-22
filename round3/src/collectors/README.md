# Round 3 Data Collectors — Event Horizon

## Sources

| Collector | Auth Required | Run Command |
|-----------|--------------|-------------|
| `gdelt_collector.py` | None | `python src/collectors/gdelt_collector.py` |
| `google_play_reviews_collector.py` | None | `python src/collectors/google_play_reviews_collector.py` |
| `reddit_collector.py` | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` env vars | `python src/collectors/reddit_collector.py` |
| `kaggle_collector.py` | `~/.kaggle/kaggle.json` | `python src/collectors/kaggle_collector.py` |

## Reddit Setup (2 minutes)

1. Go to https://www.reddit.com/prefs/apps
2. Click **"create another app"** → select type **"script"**
3. Name: `DataVortex_R3`, redirect URI: `http://localhost:8080`
4. Copy **client ID** (under app name) and **client secret**
5. Set environment variables:
   ```powershell
   $env:REDDIT_CLIENT_ID="your_client_id"
   $env:REDDIT_CLIENT_SECRET="your_secret"
   ```

## Orchestrated Collection

`scheduler.py` runs all enabled collectors every 30 minutes and appends to `data/raw/`.
```bash
python src/scheduler.py
```

## Output

Each run writes a timestamped CSV to `data/raw/`:
- `gdelt_20210901T120000Z.csv`
- `google_play_20210901T120000Z.csv`
- `reddit_20210901T120000Z.csv`

All runs are logged to `data/collection_log.csv` (timestamp, source, query, count, status).
