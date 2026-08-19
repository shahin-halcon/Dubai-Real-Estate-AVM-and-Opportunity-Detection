# Dubai Real Estate AVM & Opportunity Detection — Project Summary

## 1. What this project is

This project is an end-to-end Dubai real-estate analytics system built around one business question:

> **Given a property transaction, what is a reasonable estimated market value, and does the observed price look unusually low relative to that estimate?**

The work combines two related outcomes:

1. **Automated Valuation Model (AVM)**  
   Estimate a property's transaction value from its physical characteristics, location/project identity, and recent comparable-sales information.

2. **Opportunity Detection**  
   Identify transactions where the model indicates a meaningful valuation gap and enough confidence/evidence exists to warrant further investigation.

The final client-facing concept is intentionally simple:

**Property details → Estimated market value → Optional asking-price comparison**

The complex modelling, cleaning, leakage prevention, temporal backtesting, and robustness analysis remain behind the interface.

---

## 2. Business problem

A real-estate broker or investor does not normally want to see model coefficients, feature matrices, or statistical diagnostics.

They want to know:

- What is this property worth?
- Is the current price reasonable?
- Does it look cheap relative to comparable market evidence?
- Which properties should I investigate first?

The project was therefore designed as a **decision-support system**, not a black-box “profit guarantee”.

The correct business interpretation is:

> **The model highlights properties that appear relatively underpriced and deserve human due diligence.**

It does **not** prove that a property will definitely make a profit.

---

## 3. Data and time coverage

The main modelling dataset eventually contained:

- **79,123** historical property transactions in the modelling dataframe.
- Date range: **2026-01-01 16:21:33 → 2026-08-17 15:14:16**
- Final clean historical backtest universe: **74,252** transactions.
- Transactions with a usable 30-day forward comparable signal: **63,206**.
- Transactions with at least **3 future comparable transactions**: **50,457**.

The current production candidate set contains:

- **91** current opportunity candidates.
- **44 Conservative Opportunities**
- **47 Broad Opportunities**

The historical backtest counts are different:

- **35 historical Conservative observations**
- **27 historical Broad observations**
- **50,395 No Signal observations**

These must not be mixed together. The 44/47 split is the **current production candidate universe**; the 35/27 split is the **historical realized-backtest signal population**.

---

## 4. Important data-quality decisions

### 4.1 Why we did not blindly remove every missing value

Missing values were treated according to their meaning.

For historical/comparable features, a missing value can mean:

> “There was not enough recent transaction history to calculate a reliable comparable statistic.”

That is not the same as:

> “The row is corrupt.”

The XGBoost model can natively route missing numeric values. Therefore, where the missingness represented **lack of history**, it was retained rather than fabricating a value.

Examples:

- `area_90d_median_ppsf`
- `project_90d_median_ppsf`
- `area_90d_transaction_count`
- `project_90d_transaction_count`
- `log_area_90d_count`
- `log_project_90d_count`

This is especially important for newly launched or thinly traded projects.

### 4.2 Invalid transaction records

A later data-quality screen produced:

- **12,660** test/current rows in one validation slice.
- **12,310 VALID**
- **350 INVALID**

Invalid examples showed implausible transaction values / PPSF relationships and were excluded from the clean opportunity universe.

### 4.3 PPSF cleaning for backtesting

The raw backtest universe was:

- **74,772** rows.

After the future-comparable validity check:

- **74,252** clean rows.

This removed transactions where the future comparable calculation was not valid.

The cleaned PPSF distribution was:

- Mean: **1,976.52 AED/sqft**
- Median: **1,755.56 AED/sqft**
- Minimum: **303.44 AED/sqft**
- Maximum: **17,067.27 AED/sqft**

The reason for doing this was not to make the results look better; it was to avoid using obviously invalid PPSF observations as comparable-market evidence.

### 4.4 Future comparable requirement

The backtest was designed around a future 30-day market outcome.

Of 74,252 target transactions:

- **63,206** had at least one future 30-day comparable.
- **50,457** had at least **3** future comparables.

The primary robustness universe used 50,457 rows because a forward signal based on a single future observation is much less stable than one supported by several comparable transactions.

---

## 5. Feature engineering

The final XGBoost valuation model used exactly 12 features:

1. `log_area_sqft`
2. `bedrooms`
3. `parking_count`
4. `is_offplan`
5. `is_freehold`
6. `area_90d_median_ppsf`
7. `project_90d_median_ppsf`
8. `log_area_90d_count`
9. `log_project_90d_count`
10. `project_history_available`
11. `AREA_EN`
12. `PROJECT_EN`

### Why these features matter to the business

**Property size**  
Larger/smaller units naturally have different pricing behaviour. The logarithm makes the relationship less sensitive to extreme sizes.

**Bedrooms / unit type**  
Studios, 1-bedroom, 2-bedroom, etc. are not directly interchangeable.

**Parking**  
Parking can materially affect buyer demand and price.

**Off-plan status**  
Off-plan and ready properties can behave differently because of payment plans, launch pricing, construction stage, and resale liquidity.

**Freehold status**  
Ownership structure can influence the relevant market.

**Area 90-day median PPSF**  
Represents recent market evidence for the surrounding area.

**Project 90-day median PPSF**  
Represents more specific evidence for the project.

**Comparable transaction counts**  
Measure the depth of supporting market evidence.

**Project history availability**  
Distinguishes a project with historical evidence from one with little or no history.

**Area and project identity**  
Allow the model to learn that prices are systematically different between Dubai locations and developments.

---

## 6. Model progression

Several model versions were tested.

### Model 1A — Baseline Ridge

- MAE: **AED 284,763.71**
- RMSE: **AED 1,560,856.71**
- R²: **0.7413**
- Median Absolute % Error: **7.92%**
- Within ±10%: **58.19%**
- Within ±20%: **80.43%**

This established a credible linear baseline.

### Model 1B — Log Target Ridge + 90-day comparable features

- MAE: **AED 241,464.94**
- RMSE: **AED 1,485,365.46**
- R²: **0.7657**
- Median Absolute % Error: **7.08%**
- Within ±10%: **62.79%**
- Within ±20%: **85.07%**

The log target improved the fit substantially, especially for a highly skewed property-price distribution.

### Model 2 — XGBoost AVM

Best iteration: **986**

- MAE: **AED 214,975.47**
- RMSE: **AED 1,019,776.49**
- R²: **0.8896**
- Median Absolute % Error: **6.24%**
- Within ±10%: **67.99%**
- Within ±20%: **86.50%**

This was the strongest modelling result.

The model parameters included:

- learning rate: 0.03
- max depth: 6
- n_estimators: 2000
- min child weight: 10
- subsample: 0.8
- colsample_bytree: 0.8
- reg_alpha: 0.1
- reg_lambda: 5.0
- random state: 42

### Model 2B — Native categorical experiment

A separate native-categorical XGBoost experiment produced:

- MAE: **AED 228,770.81**
- RMSE: **AED 1,335,055.39**
- R²: **0.8107**
- Median Absolute % Error: **6.37%**
- Within ±10%: **66.82%**
- Within ±20%: **87.00%**

It did not outperform the main XGBoost result on the overall validation criteria, so the stronger Model 2 result remained the main valuation model.

---

## 7. Why the log target was useful

Property values are heavily right-skewed.

The transaction-value distribution contained very high-value properties, while the majority of transactions were much lower.

Training on:

`log_price = log(TRANS_VALUE)`

helps prevent extremely expensive properties from dominating the model's loss.

The final prediction is converted back to AED using:

`estimated_value = exp(predicted_log_value)`

This is why the production dashboard reports an actual AED value rather than a log value.

---

## 8. Comparable-sales logic

The project used recent transaction evidence at two levels:

### Area-level

Recent transactions in the same area supplied:

- 90-day median PPSF
- transaction count
- log transaction count

### Project-level

Recent transactions in the same project supplied:

- 90-day median PPSF
- transaction count
- log transaction count
- project-history flag

The intent was to avoid valuing a property purely from generic physical attributes.

A property in Dubai Marina and a property in Madinat Al Mataar can have similar size/bedroom counts and still have very different values. Recent comparable evidence helps the model capture that.

---

## 9. Leakage prevention

This was a major part of the project.

The model should only see information that could have been known at the transaction date.

Therefore:

> **Current valuation features were built from historical information available before the target transaction, not from future transactions.**

For the opportunity backtest, the opposite direction was intentionally used:

> Given a transaction at time T, look at what happened in the next 30 days and calculate the future comparable PPSF.

This future information is used **only to evaluate whether the signal would have worked**, not as a model input.

That distinction is critical.

---

## 10. Future 30-day backtest

For a target transaction at time T:

1. Identify later comparable transactions.
2. Restrict to the next 30 days.
3. Calculate the future comparable PPSF.
4. Calculate the forward return:

`future_30d_ppsf / current_ppsf - 1`

This created:

- 63,206 transactions with at least one future comparable.
- 50,457 transactions with at least 3 future comparables.

The >=3 universe became the main signal-validation dataset.

---

## 11. Opportunity signal

The valuation model itself is not enough.

The project added an opportunity layer using:

- valuation gap
- model risk
- confidence
- comparable evidence
- opportunity score

The frozen production rule became:

### Conservative Opportunity

`opportunity == HIGH OPPORTUNITY`

AND

`confidence_score >= 80`

### Broad Opportunity

`opportunity == HIGH OPPORTUNITY`

AND

`confidence_score < 80`

### No Signal

Everything else.

This rule was frozen before moving into the production-style dashboard.

---

## 12. Historical opportunity performance

On the 50,457-observation backtest:

### Conservative / High-confidence signal

- Transactions: **35**
- Median forward return: **46.69%**
- Mean forward return: **56.96%**
- Positive return rate: **100.00%**
- Above 10% return rate: **97.14%**

### Broad signal

- Transactions: **27**
- Median forward return: **28.55%**
- Mean forward return: **27.79%**
- Positive return rate: **81.48%**
- Above 10% return rate: **66.67%**

### No Signal baseline

- Transactions: **50,395**
- Median return: approximately **0%**
- Mean return: **0.65%**
- Positive rate: **48.64%**
- Above 10% rate: **9.14%**

The Conservative signal therefore showed substantial historical lift over the baseline.

---

## 13. Bootstrap statistical validation

Bootstrap 95% confidence intervals were calculated.

Conservative:

- Mean return: **44.26%**
- 95% CI: **36.40% to 52.41%**
- Median return: **35.02%**
- 95% CI: **30.22% to 46.69%**

Non-high baseline:

- Mean return: **0.65%**
- 95% CI: **0.55% to 0.76%**

Mean-return lift:

- Observed: **43.61 percentage points**
- Bootstrap 95% CI: **35.75 to 52.00 percentage points**

This gave stronger statistical evidence that the signal behaved differently from the baseline in the historical sample.

---

## 14. Robustness findings

Several robustness checks were run.

### Minimum future comparable count

Higher comparable counts generally strengthened the historical signal:

- >=5 future comps: median **43.01%**
- >=10: **46.69%**
- >=20: **54.62%**
- >=30: **59.73%**

This supports the idea that stronger comparable depth made the observed forward signal more credible.

### Transaction friction

With conservative historical trades:

- 0 pp friction: mean **56.96%**
- 5 pp: **51.96%**
- 10 pp: **46.96%**
- 20 pp: **36.96%**

The signal remained positive under substantial hypothetical friction in the historical sample.

### Extreme-winner removal

Removing the best trades did not eliminate the effect:

- Remove top 1: mean **53.70%**
- Remove top 5: mean **48.03%**
- Remove top 10: mean **41.03%**

This is valuable because it shows the headline mean was not created solely by one giant winner.

---

## 15. Concentration risk

This was one of the most important weaknesses identified.

Historical Conservative observations were concentrated in a few projects.

Top 5 projects represented approximately **64.52%** of the historical high-opportunity signal.

RAW DISTRICT BY IMTIAZ R alone represented about **37.10%** historically.

A leave-one-project-out test excluding RAW DISTRICT still left:

- **39** high-opportunity observations
- Median return: **32.61%**
- Mean return: **38.81%**
- Positive rate: **89.74%**
- >10% return rate: **84.62%**

So the signal was not solely dependent on one project, but concentration remained a real portfolio risk.

---

## 16. Important project-level limitation

Not every project performed well.

For example:

**Rome 3 by SD**

- 5 historical observations
- Median return approximately **0%**
- Mean approximately **0%**
- Positive rate: **20%**
- Above 10%: **0%**

Therefore the system should never be described as:

> “Every HIGH OPPORTUNITY property is profitable.”

The signal is a **screening mechanism**, not a guarantee.

---

## 17. Temporal holdout limitation

A temporal holdout was tested using a split date of:

**2026-06-05 12:01:04**

However, the historical rule-selection period contained **zero HIGH OPPORTUNITY observations** under the frozen signal.

The later holdout contained the signal observations.

This means the temporal holdout did not function as a perfectly independent “learn the rule on early data, prove it later” experiment.

This should be disclosed rather than hidden.

The project therefore has strong historical evidence, but the temporal validation design is **not sufficient to claim a fully independent prospective rule-selection test**.

---

## 18. Current production opportunity universe

After the research/validation work, the current production candidate universe contained:

- **91** candidates
- **44 Conservative**
- **47 Broad**

For the 44 Conservative candidates:

- Total ticket value: **AED 37.13M**
- Median ticket: **AED 717,180**
- Largest ticket: **AED 1.99M**

The leading current examples included:

- Azizi Milan 55
- RAW DISTRICT BY IMTIAZ R
- AZIZI VENICE 10
- Binghatti Luxuria
- OMYA RESIDENCES

These are **current model candidates**, not guaranteed investments.

---

## 19. Capital deployment analysis

Historical ticket sizes for the 35 backtest Conservative observations had:

- Median ticket: about **AED 708,882**
- Total historical ticket value: **AED 27.94M**

Current production candidates had a larger total ticket pool.

A score-ranked capital simulation was used to understand deployability.

Example current production scenarios:

### AED 1M

The unrestricted score-ranked approach could deploy approximately **AED 980K** across 2 transactions.

### AED 5M

Approximately **AED 4.79M** could be deployed across 6 transactions.

### AED 10M

Approximately **AED 9.61M** could be deployed across 10 transactions.

A project-level concentration cap was also tested.

For AED 10M with a 20% project cap:

- **13 transactions**
- **AED 9.72M deployed**
- about **97.2% utilization**

The purpose was not to predict profit. It was to understand how the opportunity set would translate into actual transaction sizes and concentration constraints.

---

## 20. Production model export

The trained valuation model was exported as:

`valuation_model.joblib`

The model expects 12 features in the exact order:

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

The exact training categories were also exported:

`model_categories.json`

with:

- **124 area categories**
- **2,110 project categories**

The category representation was confirmed from `X_train`, where `AREA_EN` and `PROJECT_EN` were pandas categorical features.

Area/project historical lookup files were exported:

- `area_reference.csv`
- `project_reference.csv`

---

## 21. Final client-facing product concept

The final business-facing application is intentionally simple.

A broker enters:

- Area
- Project
- Property type
- Property size
- Parking
- Off-plan / Ready
- Freehold
- Optional asking price

The app then returns:

### Estimated Market Value

Example format:

`AED 1.25M`

### Estimated Value per Sq Ft

Example:

`AED 1,470 / sqft`

### Optional Asking Price Comparison

If the broker enters AED 1.05M:

- Asking price
- Estimated value
- Difference
- Percentage below/above the estimate

That is the intended client experience.

---

## 22. Critical current limitation of the Streamlit prototype

During user testing, the exported model sometimes produced property-level estimates that varied materially from actual values, including cases around 10% and cases around 50% error.

This means the current Streamlit inference layer should be treated as a **prototype requiring further inference calibration/verification**, even though the offline model evaluation was strong.

The likely area to validate next is the exact reconstruction of the training-time historical comparable features and inference-time feature availability. The categorical representation has already been identified and exported; the remaining production concern is making sure a new property's input features reproduce the same logic used during model training.

This limitation should be explicitly stated in the project documentation.

---

## 23. What the project demonstrates professionally

The project demonstrates the ability to:

- translate a real business problem into a measurable ML problem;
- clean and validate transactional data;
- think about missingness semantically rather than mechanically;
- build comparable-sales features;
- compare baseline and nonlinear models;
- avoid obvious forward leakage;
- evaluate models with both absolute and percentage metrics;
- construct a business opportunity signal;
- perform temporal and robustness analysis;
- quantify concentration and deployment constraints;
- export a production-style model;
- build a simple user-facing application;
- recognize and document model limitations rather than hiding them.

---

## 24. Recommended project positioning

### Strong resume title

**Dubai Real Estate Automated Valuation & Opportunity Detection System**

### One-line description

> Built a Dubai real-estate AVM using historical transaction and recent comparable-sales data, then layered a high-confidence opportunity screen and broker-facing valuation application on top.

### Interview positioning

The strongest story is not:

> “I built an XGBoost model.”

It is:

> “I built an end-to-end property valuation and opportunity-screening system for Dubai real estate. I started with a simple valuation baseline, added recent area/project comparable evidence, improved the model with XGBoost, then tested whether the resulting price-dislocation signal had historical forward value. Finally, I converted the research output into a simple broker-facing property value estimator.”

That demonstrates both analytics and business thinking.
