import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from scipy.sparse import csr_matrix

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.preprocess import load_and_audit, apply_cleaning, RANDOM_STATE

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")

def main():
    print("=" * 70)
    print("RUNNING NEAR-DUPLICATE LEAKAGE AUDIT & 5-FOLD CROSS-VALIDATION")
    print("=" * 70)

    df, audit = load_and_audit(DATA_PATH)
    df, empty = apply_cleaning(df)
    
    print(f"Total clean rows: {len(df)}")
    print(f"Exact duplicates removed during initial audit: {audit['duplicate_rows_removed']}")

    from sklearn.model_selection import train_test_split
    train_df, test_df = train_test_split(
        df, test_size=0.20, random_state=RANDOM_STATE, stratify=df["sentiment_label"]
    )
    
    train_texts = train_df["cleaned_text"].tolist()
    test_texts = test_df["cleaned_text"].tolist()
    train_ids = train_df.index.tolist()
    test_ids = test_df.index.tolist()

    print("\n--- TASK 1: NEAR-DUPLICATE LEAKAGE AUDIT ---")
    
    cv = CountVectorizer(ngram_range=(3, 3), binary=True, min_df=1)
    X_train_grams = cv.fit_transform(train_texts)
    X_test_grams = cv.transform(test_texts)
    
    # Calculate word 3-gram Jaccard similarity between test set and train set
    # Jaccard(A, B) = |A ∩ B| / |A ∪ B| = dot(A, B) / (sum(A) + sum(B) - dot(A, B))
    train_gram_counts = X_train_grams.sum(axis=1).A1
    test_gram_counts = X_test_grams.sum(axis=1).A1
    
    near_duplicates = []
    
    # Batch processing test samples against train matrix
    batch_size = 200
    for start in range(0, len(test_texts), batch_size):
        end = min(start + batch_size, len(test_texts))
        test_batch = X_test_grams[start:end]
        
        # Intersections
        intersections = (test_batch @ X_train_grams.T).toarray() # shape (batch, n_train)
        
        for i_local in range(end - start):
            te_idx_global = start + i_local
            te_count = test_gram_counts[te_idx_global]
            if te_count == 0:
                continue
            
            # Vectorized Jaccard formula for batch item i_local across all train
            inters = intersections[i_local]
            unions = te_count + train_gram_counts - inters
            jaccard_scores = np.divide(inters, unions, out=np.zeros_like(inters, dtype=float), where=unions!=0)
            
            high_matches = np.where(jaccard_scores >= 0.80)[0]
            for tr_match_idx in high_matches:
                te_orig_idx = test_ids[te_idx_global]
                tr_orig_idx = train_ids[tr_match_idx]
                j_score = jaccard_scores[tr_match_idx]
                near_duplicates.append((te_orig_idx, tr_orig_idx, j_score, test_texts[te_idx_global], train_texts[tr_match_idx]))

    print(f"Near-duplicate threshold: Jaccard >= 0.80 on word 3-grams")
    print(f"Total near-duplicates straddling Train/Test split: {len(near_duplicates)}")
    
    if len(near_duplicates) > 0:
        print("\nSample Train/Test Near-Duplicates:")
        for te_i, tr_i, jacc, te_t, tr_t in near_duplicates[:5]:
            print(f"  Test [{te_i}]: {te_t[:80]}")
            print(f"  Train [{tr_i}]: {tr_t[:80]}")
            print(f"  Jaccard Sim: {jacc:.4f}\n")
    else:
        print("✓ Zero near-duplicates found between Train and Test split at threshold 0.80.")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), max_features=50_000,
            sublinear_tf=True, min_df=2, strip_accents="unicode"
        )),
        ("clf", LinearSVC(
            C=1.0, max_iter=2000,
            class_weight="balanced", random_state=RANDOM_STATE
        ))
    ])

    pipeline.fit(train_df["cleaned_text"], train_df["sentiment_label"])
    y_test_pred = pipeline.predict(test_df["cleaned_text"])
    orig_acc = accuracy_score(test_df["sentiment_label"], y_test_pred)
    orig_f1 = f1_score(test_df["sentiment_label"], y_test_pred, average="macro")
    print(f"\nOriginal Single Split Test Accuracy: {orig_acc:.4f} ({orig_acc*100:.2f}%), Macro-F1: {orig_f1:.4f}")

    if len(near_duplicates) > 0:
        leaked_test_indices = [x[0] for x in near_duplicates]
        clean_test_df = test_df.drop(index=leaked_test_indices)
        clean_y_pred = pipeline.predict(clean_test_df["cleaned_text"])
        clean_acc = accuracy_score(clean_test_df["sentiment_label"], clean_y_pred)
        clean_f1 = f1_score(clean_test_df["sentiment_label"], clean_y_pred, average="macro")
        print(f"Purged Single Split Test Accuracy (without leaked test samples): {clean_acc:.4f} ({clean_acc*100:.2f}%), Macro-F1: {clean_f1:.4f}")
        print(f"Leakage Impact: Accuracy shift = {(clean_acc - orig_acc)*100:+.2f} percentage points")

    print("\n--- TASK 2: 5-FOLD STRATIFIED CROSS-VALIDATION ---")
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    
    X = df["cleaned_text"].values
    y = df["sentiment_label"].values
    
    fold_accuracies = []
    fold_macro_f1s = []
    fold_weighted_f1s = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]
        
        fold_pipe = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), max_features=50_000,
                sublinear_tf=True, min_df=2, strip_accents="unicode"
            )),
            ("clf", LinearSVC(
                C=1.0, max_iter=2000,
                class_weight="balanced", random_state=RANDOM_STATE
            ))
        ])
        
        fold_pipe.fit(X_tr, y_tr)
        preds = fold_pipe.predict(X_val)
        
        acc = accuracy_score(y_val, preds)
        macro_f1 = f1_score(y_val, preds, average="macro")
        weighted_f1 = f1_score(y_val, preds, average="weighted")
        
        fold_accuracies.append(acc)
        fold_macro_f1s.append(macro_f1)
        fold_weighted_f1s.append(weighted_f1)
        print(f"  Fold {fold}: Accuracy = {acc:.4f} ({acc*100:.2f}%), Macro-F1 = {macro_f1:.4f}")

    mean_acc = np.mean(fold_accuracies)
    std_acc = np.std(fold_accuracies)
    mean_mf1 = np.mean(fold_macro_f1s)
    std_mf1 = np.std(fold_macro_f1s)

    print("\n" + "="*70)
    print("5-FOLD CV SUMMARY REPORT")
    print("="*70)
    print(f"Mean Accuracy : {mean_acc:.4f} ± {std_acc:.4f} ({mean_acc*100:.2f}% ± {std_acc*100:.2f}%)")
    print(f"Mean Macro-F1 : {mean_mf1:.4f} ± {std_mf1:.4f} ({mean_mf1*100:.2f}% ± {std_mf1*100:.2f}%)")
    print(f"Accuracy Std  : {std_acc*100:.2f} percentage points")
    print(f"Macro-F1 Std  : {std_mf1*100:.2f} percentage points")
    
    if std_acc * 100 > 1.5 or std_mf1 * 100 > 1.5:
        print("⚠️ HIGH VARIANCE: Standard deviation > 1.5 percentage points. Single split numbers are noisy!")
    else:
        print("✓ LOW VARIANCE: Standard deviation is under 1.5 percentage points. Single-split results are representative and stable.")

if __name__ == "__main__":
    main()
