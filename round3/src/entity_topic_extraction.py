"""
entity_topic_extraction.py - NER + Trending Term Extraction
Data Vortex A'26 | Team: Event Horizon

Uses spaCy for Named Entity Recognition and TF-IDF/frequency for
trending term extraction per time bucket (daily/weekly).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob
import json
import pandas as pd
from collections import Counter
from datetime import datetime, timezone
from config import DATA_PROC_DIR, REPORTS_DIR, TOPIC_SLUG

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except Exception:
    SPACY_AVAILABLE = False
    print("[WARN] spaCy model not loaded. Run: python -m spacy download en_core_web_sm")

ENTITY_TYPES = {"ORG", "PERSON", "GPE", "PRODUCT", "LAW", "NORP", "EVENT"}
STOPWORDS_EXTRA = {
    "whatsapp", "privacy", "policy", "app", "use", "using", "used",
    "like", "just", "one", "would", "also", "new", "even", "know",
    "people", "time", "thing", "way", "get", "got", "much", "many",
}

def get_latest_scored_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_scored_*.csv")))
    if not files:
        files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_*.csv")))
    if not files:
        raise FileNotFoundError("No scored/merged CSV found. Run preprocess.py + apply_model.py first.")
    return files[-1]

def extract_entities_batch(texts: list) -> list:
    if not SPACY_AVAILABLE:
        return [[] for _ in texts]
    results = []
    for doc in nlp.pipe(texts, batch_size=256, disable=["parser", "lemmatizer"]):
        ents = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in ENTITY_TYPES]
        results.append(ents)
    return results

def trending_terms(texts: list, top_n: int = 20) -> list:
    from sklearn.feature_extraction.text import TfidfVectorizer
    if len(texts) < 5:
        words = " ".join(texts).lower().split()
        return Counter(w for w in words if len(w) > 3 and w not in STOPWORDS_EXTRA).most_common(top_n)
    try:
        vec = TfidfVectorizer(max_features=500, stop_words="english",
                               ngram_range=(1, 2), min_df=2)
        vec.fit_transform(texts)
        scores = vec.idf_
        terms = vec.get_feature_names_out()
        top = sorted(zip(terms, scores), key=lambda x: -x[1])
        filtered = [(t, s) for t, s in top if not any(sw in t for sw in STOPWORDS_EXTRA)]
        return filtered[:top_n]
    except Exception:
        return []

def run_extraction(bucket_freq: str = "W") -> dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_path = get_latest_scored_csv()
    print(f"[Entity] Loading: {os.path.basename(csv_path)}")
    df = pd.read_csv(csv_path, low_memory=False)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"])
    df["bucket"] = df["ts"].dt.to_period(bucket_freq).astype(str)

    print(f"[Entity] Running NER on {len(df):,} rows ...")
    texts = df["text"].fillna("").astype(str).tolist()
    entity_lists = extract_entities_batch(texts)
    df["entities"] = entity_lists

    global_ents: Counter = Counter()
    for elist in entity_lists:
        for ent_text, _ in elist:
            global_ents[ent_text.lower()] += 1

    bucket_results = {}
    for bucket, group in df.groupby("bucket"):
        bucket_texts = group["text"].fillna("").astype(str).tolist()
        terms = trending_terms(bucket_texts)
        all_bucket_ents: Counter = Counter()
        for elist in group["entities"]:
            if isinstance(elist, list):
                for et, _ in elist:
                    all_bucket_ents[et.lower()] += 1
        bucket_results[str(bucket)] = {
            "n_posts": len(group),
            "trending_terms": [(t, round(s, 4)) for t, s in terms],
            "top_entities": all_bucket_ents.most_common(15),
            "sentiment_dist": group["sentiment_label"].value_counts().to_dict() if "sentiment_label" in group.columns else {},
        }

    output = {
        "global_top_entities": global_ents.most_common(30),
        "buckets": bucket_results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join(REPORTS_DIR, "entity_topic_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"[Entity] Saved -> {out_path}")
    return output

if __name__ == "__main__":
    print("=== Entity & Topic Extraction ===")
    results = run_extraction(bucket_freq="W")
    print(f"Buckets analyzed: {len(results['buckets'])}")
    print(f"Top entities: {results['global_top_entities'][:10]}")
