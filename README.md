# Dubai Real Estate Automated Valuation & Opportunity Detection

An end-to-end Dubai real-estate analytics project that estimates property value from transaction history and recent comparable-sales information, then identifies potential pricing dislocations for further investigation.

The final user-facing concept is deliberately simple:

> **Enter property details → Get estimated market value → Compare optional asking price**

---

## Project objective

The business problem is straightforward:

**Can we use historical Dubai property transactions to estimate a reasonable market value for a property, and identify cases where the observed price appears materially below that estimate?**

The project therefore has two layers:

1. **Automated Valuation Model (AVM)**
2. **Opportunity Detection / Screening**

The system is a decision-support tool. It is **not** a guaranteed-profit engine.

---

## What the project contains

### Research / modelling layer

- Data cleaning and validation
- Property feature engineering
- Recent comparable-sales features
- Baseline Ridge models
- Log-target valuation model
- XGBoost AVM
- Opportunity signal
- Temporal backtesting
- Bootstrap confidence intervals
- Concentration analysis
- Transaction-friction sensitivity
- Future-comparable robustness
- Capital deployment analysis

### Client-facing layer

A simple Streamlit property valuation page where a real-estate user can enter:

- Area
- Project
- Property type
- Property size
- Parking
- Off-plan / Ready
- Freehold
- Optional asking price

The application returns:

- Estimated market value
- Estimated AED/sqft
- Optional asking-price difference

---

## Key modelling result

The strongest offline valuation model was the XGBoost AVM.

### XGBoost AVM

- MAE: **AED 214,975**
- RMSE: **AED 1,019,776**
- R²: **0.8896**
- Median Absolute % Error: **6.24%**
- Within ±10%: **67.99%**
- Within ±20%: **86.50%**
- Best iteration: **986**

The model used a log-price target.

---

## Model features

The final model uses 12 features:

```text
log_area_sqft
bedrooms
parking_count
is_offplan
is_freehold
area_90d_median_ppsf
project_90d_median_ppsf
log_area_90d_count
log_project_90d_count
project_history_available
AREA_EN
PROJECT_EN
```

The comparable-sales features capture recent market conditions at:

- area level
- project level

while counts indicate the depth of supporting evidence.

---

## Why missing values were not all removed

A missing comparable feature often means:

> **There was not enough recent transaction history to calculate a meaningful statistic.**

That is different from a corrupt record.

For this reason, missing historical/comparable features such as:

- area 90-day median PPSF
- project 90-day median PPSF
- comparable counts
- log comparable counts

were retained when the missingness represented lack of history.

XGBoost can natively handle missing numeric values.

This is preferable to inventing a median or zero that would falsely claim evidence existed.

---

## Data-quality process

The project applied multiple quality controls.

The historical modelling dataframe contained:

**79,123 transactions**

The backtest universe began at:

**74,772 transactions**

After future-comparable validity filtering:

**74,252 transactions**

Transactions with at least one future 30-day comparable:

**63,206**

Transactions with at least three future 30-day comparables:

**50,457**

An additional data-quality screen identified invalid transaction rows and removed them from the production opportunity universe.

---

## Opportunity signal

The valuation model was converted into a business-facing opportunity screen.

### Conservative Opportunity

```text
opportunity == HIGH OPPORTUNITY
AND
confidence_score >= 80
```

### Broad Opportunity

```text
opportunity == HIGH OPPORTUNITY
AND
confidence_score < 80
```

### No Signal

All other transactions.

---

## Historical opportunity results

On the 50,457-observation historical backtest:

### Conservative

- 35 observations
- Median forward return: **46.69%**
- Mean forward return: **56.96%**
- Positive rate: **100.00%**
- Above 10%: **97.14%**

### Broad

- 27 observations
- Median forward return: **28.55%**
- Mean forward return: **27.79%**
- Positive rate: **81.48%**
- Above 10%: **66.67%**

### No Signal baseline

- 50,395 observations
- Mean forward return: **0.65%**
- Positive rate: **48.64%**
- Above 10%: **9.14%**

These are **historical backtest results**, not forecasts for current properties.

---

## Statistical validation

Bootstrap analysis produced:

### Conservative mean return

**44.26%**

95% confidence interval:

**36.40% – 52.41%**

### Conservative median

**35.02%**

95% confidence interval:

**30.22% – 46.69%**

### Mean-return lift over baseline

Observed:

**43.61 percentage points**

Bootstrap 95% confidence interval:

**35.75 – 52.00 percentage points**

---

## Robustness

The signal was checked against:

- minimum future comparable count
- transaction friction
- extreme winner removal
- project concentration
- confidence thresholds
- opportunity-score thresholds
- leave-one-project-out analysis

Removing the top 10 historical winners still left:

- Mean return: **41.03%**
- Median return: **43.01%**
- Positive rate: **100%**

The signal also remained positive under substantial hypothetical transaction friction.

---

## Important limitations

### 1. Concentration

The opportunity signal is concentrated in a small number of projects.

RAW DISTRICT BY IMTIAZ R represented a large share of the historical opportunity set.

Current production opportunities also remain concentrated.

This is a meaningful portfolio risk.

### 2. Not every project works equally well

Some projects had weak historical performance within the signal, demonstrating that the opportunity system is a screening mechanism rather than a guarantee.

### 3. Temporal holdout limitation

The attempted rule-selection period contained zero high-opportunity observations before the split date.

Therefore the temporal holdout is **not a perfect independent rule-selection experiment**.

This is disclosed rather than hidden.

### 4. Current Streamlit inference needs additional validation

The offline valuation model performed strongly, but the first Streamlit prototype produced some individual estimates that differed materially from actual values.

The exact categorical representation used during training has been recovered, but the full training-time comparable-feature construction should be verified against live inference before treating the dashboard as production-grade valuation infrastructure.

---

## Production assets

The dashboard valuation engine uses:

```text
model/
├── valuation_model.joblib
├── valuation_model_metadata.json
├── model_categories.json
├── area_reference.csv
└── project_reference.csv
```

The exported research data includes:

```text
data/
├── production_candidates.csv
├── backtest_30d.csv
└── metadata.json
```

---

## Running the Streamlit application

From the dashboard directory:

```bash
pip install streamlit pandas numpy joblib xgboost
```

Then:

```bash
streamlit run visualize_broker_final.py
```

The app is intended to be a single-page, non-technical interface.

---

## User flow

```text
Area
  ↓
Project
  ↓
Property Type
  ↓
Size
  ↓
Parking
  ↓
Off-Plan / Ready
  ↓
Freehold
  ↓
[ Estimate Market Value ]
  ↓
Estimated Market Value
  +
Estimated AED / sqft
  +
Optional Asking Price Comparison
```

---

## Example business interpretation

Suppose the broker enters:

- Area: JVC
- Project: Example Project
- Property type: 1 B/R
- Size: 850 sqft
- Parking: 1
- Off-plan: Yes
- Freehold: Yes
- Asking price: AED 1.05M

The application returns:

- estimated market value
- estimated AED/sqft
- difference between asking price and estimated value

The broker then decides whether the property deserves further due diligence.

The system does **not** tell the broker:

> “You will definitely make a profit.”

It tells the broker:

> **“Based on the trained valuation model and available market evidence, this is the estimated value.”**

---

## Project structure

```text
dashboard/
├── data/
│   ├── backtest_30d.csv
│   ├── metadata.json
│   └── production_candidates.csv
│
├── model/
│   ├── area_reference.csv
│   ├── model_categories.json
│   ├── project_reference.csv
│   ├── valuation_model_metadata.json
│   └── valuation_model.joblib
│
├── requirements.txt
└── visualize_broker.py
│
dataset/
└── transactions-2026-08-17.csv
│
Documentation/
├── PROJECT_DOCUMENTATION.md
├── PROJECT_SUMMARY.md
└── eval.txt
│
feature_engineering.ipynb
feature_testing(opt.).ipynb
The broader research notebook contains the modelling, validation, backtesting, and opportunity-analysis workflow.
```


---

