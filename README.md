
# 🚀 Checkout Experiment & Growth Analytics System

**Cap + Flag Revenue Logic | Frequentist A/B Testing | 30-Day Financial Forecasting**

## 📌 Project Overview

#### This project is an end-to-end data science and product analytics pipeline designed to evaluate a new checkout experience (**Variant B**). By merging granular event logs with transactional data, the system diagnoses funnel friction, identifies high-growth user segments, and provides a statistically backed "Go/No-Go" recommendation for product rollout.

### 🔑 Key Findings

#### * **The "Intent vs. Friction" Paradox:** Variant B drove a **+18.7% lift in Session CVR**, but introduced a **37.6s speed penalty** ($p=0.035$).
#### * **Super-Winner Segments:** **Search Traffic (+48.6% lift)** and **New Users (+34.5% lift)** showed massive outperformance.
#### * **Final Verdict:** **ITERATE.** Recommendation is to optimize technical latency before a 100% rollout.

---

## 🛠️ Setup & Installation

#### 1. **Environment Setup:**
##### Ensure you have Python 3.8+ installed. Install dependencies:
```bash
pip install pandas numpy matplotlib seaborn scipy statsmodels plotly

```
#### 2. Project Directory Structure
##### To run the scripts successfully, organize your local folders as follows:
#### * data/: Destination for generated Fact and Dimension tables.
#### * etl/: Destination for diagnostic plots (e.g., Outlier Boxplots).
#### * raw_data/: Place your source files here (campaigns.csv, events.csv, orders.csv, etc.).

#### 3. **Data Placement:**
#### Place raw `.csv` and `.json` files in the `/raw_data` folder.

---

## 🔄 ETL & Analytics Pipeline (End-to-End)

#### The system is designed to run sequentially to ensure data integrity:

### 1. Data Transformation (`etl.py`)

#### * **Standardization:** Cleans inconsistent casing and strips whitespace across all tables.
#### * **Outlier Mitigation:** Implements **Cap + Flag** logic using the **1.5 * IQR method** on revenue columns to prevent "whale" purchases from skewing the mean.
#### * **Feature Engineering:** Calculates `margin_proxy`, `time_to_step`, and `funnel_flags`.

### 2. Statistical Engine (`analysis.py`)

#### * **Sanity Checks:** Performs a **Chi-Square test** for Sample Ratio Mismatch (SRM) to ensure a balanced 50/50 split.
#### * **Hypothesis Testing:** Runs **Z-tests for proportions** (CVR/CCR) and **T-tests** for continuous metrics (Revenue/Time).
#### * **HTE Analysis:** Breaks down the "Treatment Effect" across Device, Channel, and City Tier.

### 3. Financial Projection (`analysis.py`)

#### * **Scenario Modeling:** Generates **Best/Base/Worst-case** 30-day revenue forecasts based on incremental lift and seasonal patterns.
#### * **Sensitivity Analysis:** Applies a $\pm5\%$ range to ensure conservative business estimates.

---

## 📊 Data Outputs Generated

#### The pipeline exports cleaned, analysis-ready files to the `/data` directory:

#### * **`fact_sessions.csv`**: The primary analytical grain (1 row per session) with all funnel timestamps.
#### * **`fact_orders.csv`**: Enriched order data including category mix (JSON) and margin proxies.
#### * **`dim_users_enriched.csv`**: Comprehensive user profiles with lifetime value (LTV) bands and repeat-rate flags.
#### * **`experiment_results.csv`**: A "Cheat Sheet" for BI tools containing all p-values, lifts, and financial impact ranges.

---

## 📈 Dashboard & Visualization

#### * **Tool Used:** **Tableau Desktop / Public**
#### * **How to Open:**
##### 1. Open the provided `.twbx` file in Tableau.
##### 2. Connect the data source to `experiment_results.csv` and `fact_sessions.csv`.


#### * **Dashboard Features:**
#### * **Segment Explorer:** Interactive heatmaps for HTE-Lite analysis.
#### * **Funnel Diagnostics:** Visualizing the 29.3% "Final Leak" at the payment stage.
#### * **Executive Summary:** High-level North Star metrics vs. Speed Penalties.

---

## 🚀 Final Strategic Roadmap

#### > **Recommendation:** Do not roll out to 100% yet.
#### > 1. **Fix Latency:** Reduce the 28.5s checkout delay.
#### > 2. **Targeted Rollout:** Enable Variant B for **Search** and **New Users** immediately to capture the **₹249k/month** upside.
#### > 3. **Re-Test:** Re-evaluate "Returning Users" after speed optimizations.
