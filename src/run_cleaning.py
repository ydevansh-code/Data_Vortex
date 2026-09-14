import logging, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean_data as cd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
log = logging.getLogger(__name__)

USERS_RAW   = os.path.join('data','raw','users_raw.csv')
POSTS_RAW   = os.path.join('data','raw','posts_raw.csv')
USERS_CLEAN = os.path.join('data','cleaned','users_clean.csv')
POSTS_CLEAN = os.path.join('data','cleaned','posts_clean.csv')
MERGED_OUT  = os.path.join('data','cleaned','merged_summary.csv')
VALID_PLATS = {'YouTube','Facebook','Twitter','Reddit','Instagram'}


def _parse_ts(series):
    result = pd.Series(pd.NaT, index=series.index, dtype='datetime64[ns]')
    num_mask = pd.to_numeric(series, errors='coerce').notna()
    if num_mask.any():
        result[num_mask] = pd.to_datetime(
            pd.to_numeric(series[num_mask], errors='coerce'), unit='s', errors='coerce')
    dmy = (~num_mask) & series.str.match(r'^\d\d-\d\d-\d{4}' + '$', na=False)
    if dmy.any():
        result[dmy] = pd.to_datetime(series[dmy], format='%d-%m-%Y', errors='coerce')
    rest = (~num_mask) & (~dmy) & series.notna()
    if rest.any():
        result[rest] = pd.to_datetime(series[rest], errors='coerce')
    return result


def _clean_text(s):
    s = s.astype(str)
    s = s.str.replace('<[^>]+>', ' ', regex=True)
    s = s.str.replace('[&]amp;|[&]lt;|[&]gt;|[&]quot;', ' ', regex=True)
    s = s.str.replace('Ã©|Ã\xa0|Ã¨', '', regex=False)
    s = s.str.replace(r'\s{2,}', ' ', regex=True).str.strip()
    return s.replace({'nan': np.nan, '': np.nan, 'None': np.nan})


def clean_users():
    log.info('=== CLEANING USERS ===')
    df = cd.load_raw(USERS_RAW)
    df = cd.validate(df)
    df = cd.replace_placeholders(df)
    df = cd.handle_missing(df, config={
        'follower_count': 'median',
        'account_created': 'flag',
        'location': 'flag',
        'language': 'flag',
    })
    df['account_created'] = _parse_ts(
        df['account_created'].astype(str).replace('nan', np.nan)
    ).dt.strftime('%Y-%m-%d')
    df['follower_count'] = pd.to_numeric(df['follower_count'], errors='coerce')
    df['language'] = df['language'].str.strip().str.lower()
    df['location'] = df['location'].str.strip()
    df = cd.deduplicate(df, subset=['user_id'])
    os.makedirs(os.path.dirname(USERS_CLEAN), exist_ok=True)
    df.to_csv(USERS_CLEAN, index=False, encoding='utf-8-sig')
    df.to_json(USERS_CLEAN.replace('.csv', '.json'), orient='records', indent=2)
    n = len(df)
    cd._record('export', 'ALL', 'write_csv', n, 'Exported ' + str(n) + ' users to ' + USERS_CLEAN)
    log.info('Users -> %s  (%d rows x %d cols)', USERS_CLEAN, *df.shape)
    return df


def clean_posts():
    log.info('=== CLEANING POSTS ===')
    df = cd.load_raw(POSTS_RAW)
    df = cd.validate(df)
    df = cd.replace_placeholders(df)
    df['platform_was_null'] = (~df['platform'].isin(VALID_PLATS)).astype(int)
    bad_n = int(df['platform_was_null'].sum())
    df.loc[~df['platform'].isin(VALID_PLATS), 'platform'] = np.nan
    cd._record('missing', 'platform', 'flag_invalid', bad_n,
               'Flagged ' + str(bad_n) + ' invalid/null platform values (NULL string + NaN)')
    df['text_content'] = _clean_text(df['text_content'])
    ok_n = int(df['text_content'].notna().sum())
    cd._record('standardize', 'text_content', 'strip_html', ok_n,
               'Stripped HTML tags, entities, mojibake from text_content')
    df['_ts_parsed'] = _parse_ts(df['timestamp'].astype(str).replace('nan', np.nan))
    ts_ok = int(df['_ts_parsed'].notna().sum())
    ts_fail = int(df['_ts_parsed'].isna().sum())
    cd._record('standardize', 'timestamp', 'multi_format_parse', ts_ok,
               'Parsed ' + str(ts_ok) + ' timestamps (ISO8601 / DD-MM-YYYY / Unix epoch); '
               + str(ts_fail) + ' remain null')
    df['timestamp'] = df['_ts_parsed'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    df.drop(columns=['_ts_parsed'], inplace=True)
    for col in ('likes', 'shares', 'comments'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
        n_null = int(df[col].isna().sum())
        if n_null:
            med = df[col].median()
            df[col] = df[col].fillna(med)
            cd._record('missing', col, 'median_impute', n_null,
                       'Imputed ' + str(n_null) + ' null ' + col + ' with median=' + str(round(med)))
    df = cd.deduplicate(df, subset=['post_id'])
    os.makedirs(os.path.dirname(POSTS_CLEAN), exist_ok=True)
    df.to_csv(POSTS_CLEAN, index=False, encoding='utf-8-sig')
    df.to_json(POSTS_CLEAN.replace('.csv', '.json'), orient='records', indent=2)
    n = len(df)
    cd._record('export', 'ALL', 'write_csv', n, 'Exported ' + str(n) + ' posts to ' + POSTS_CLEAN)
    log.info('Posts -> %s  (%d rows x %d cols)', POSTS_CLEAN, *df.shape)
    return df


def build_merged(users, posts):
    agg = posts.groupby('user_id').agg(
        total_posts=('post_id', 'count'),
        total_likes=('likes', 'sum'),
        total_shares=('shares', 'sum'),
        total_comments=('comments', 'sum'),
        avg_likes=('likes', 'mean'),
        platforms_used=('platform', lambda x: x.dropna().nunique()),
    ).reset_index()
    merged = users.merge(agg, on='user_id', how='left')
    merged['engagement_score'] = (
        merged['avg_likes'].fillna(0) * 0.5
        + merged['total_shares'].fillna(0) * 0.3
        + merged['total_comments'].fillna(0) * 0.2
    )
    merged.to_csv(MERGED_OUT, index=False, encoding='utf-8-sig')
    merged.to_json(MERGED_OUT.replace('.csv', '.json'), orient='records', indent=2)
    n = len(merged)
    cd._record('export', 'merged', 'left_join', n, 'Merged users+posts -> ' + MERGED_OUT)
    log.info('Merged -> %s  (%d rows)', MERGED_OUT, n)
    return merged


if __name__ == '__main__':
    u = clean_users()
    p = clean_posts()
    m = build_merged(u, p)
    log.info('DONE. Users=%d  Posts=%d  Merged=%d', len(u), len(p), len(m))
    cd._flush_change_log()
