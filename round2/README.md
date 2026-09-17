# Data Vortex A'26 — Round 2 (NLP Semantic Engine)

> **Team: Event Horizon**  
> **Module:** Social Engine Semantic Comprehension Layer (Sentiment & Topic Classification)

---

## Quick Start

```bash
# 1. Install Round 2 dependencies
pip install -r round2/requirements.txt

# 2. Run EDA & Model Training Pipeline
python round2/src/train.py

# 3. Generate Technical Report PDF
python round2/src/generate_pdf.py
```

---

## Directory Structure

```
round2/
├── Data/
│   └── Labeled_Social_NLP_Training_Data.csv  # 9,001 labeled social posts
├── notebooks/                                # Exploratory Data Analysis & Modeling
├── models/                                   # Serialized model artifacts (.pkl)
├── reports/                                  # Figures & final Technical Report PDF
├── src/                                      # Pipeline scripts (preprocessing, training, evaluation)
├── decisions.md                              # Methodological decision log
├── implementation_plan.md                    # Approved implementation plan
├── requirements.txt                          # Pinned dependencies
└── README.md                                 # Overview & replication guide
```
