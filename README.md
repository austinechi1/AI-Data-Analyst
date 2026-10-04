# AI Data Analyst — Ask Your Data

**AI-powered data analytics application that allows users to upload CSV or Excel datasets, explore data quality, generate KPIs and visualizations, execute natural-language SQL queries, and interact with an AI assistant to obtain data-driven business insights.**

Built with Python, Pandas, SQL (SQLite), Plotly, Streamlit and the OpenAI API.

> **AI-assisted, not AI-replaced.** The AI writes SQL or Pandas code; the application runs that code on the real data and shows it to the user. Every number can be traced back to a query.

---

## Project Overview
A non-technical business user uploads a sales file and, within seconds, sees a profile of the data, a data quality report, headline KPIs and charts. They can then ask questions in plain English (*"Which country generates the most revenue?"*) and get a direct answer, the calculation behind it, a chart, a business interpretation and a suggested next question.

## Business Problem
Small and mid-sized businesses collect sales data but often lack the time or skills to analyse it. Spreadsheets hide data quality problems, and general-purpose AI chatbots can "hallucinate" numbers. Managers need fast answers they can trust.

## Project Objectives
- Profile and clean messy real-world data automatically
- Calculate standard sales KPIs and visualise trends
- Let users query data in plain English **without losing transparency**: show the SQL/Python used
- Separate **calculated facts**, **interpretations** and **recommendations**
- Package the findings into a downloadable report

## Features
| Area | What it does |
|---|---|
| Upload | CSV and Excel (.xlsx), with automatic encoding fallback |
| Dataset profile | Rows, columns, data types, missing values, duplicates; detects date / numerical / categorical columns |
| Data quality | Missing values, duplicates, invalid dates, negative quantities and prices, zero prices, extreme values, wrong data types, each with its business consequence |
| Cleaning | Removes duplicates, cancellations/returns and invalid prices (each switchable); adds `Revenue = Quantity × UnitPrice` |
| Dashboard | Period and country filters; KPI cards with sparklines and change vs previous period; trend, country and product charts; business summary (calculated, optionally rewritten by AI) |
| KPIs | Total revenue, orders, customers, average order value, units sold, units per order |
| Charts | Revenue over time (line), by country (bar), top products (horizontal bar), order values (histogram), correlation (heatmap) |
| SQL Mode | Example queries, a SQL editor, and natural-language → SQL with the generated query shown before running |
| AI Assistant | Chat with follow-up memory ("what was **its** average order value?"); answers with result table, chart and code |
| Business Insights | Rule-based, calculated insights with *why it matters*, plus optional AI recommendations |
| Report | One-click downloadable HTML report (printable to PDF) |

## Technology Stack
Python · Pandas · NumPy · SQLite · Plotly · Streamlit · OpenAI API · python-dotenv · pytest · Git/GitHub

## Architecture
```
            ┌──────────── Streamlit UI (app.py + pages/) ────────────┐
 Upload ──▶ │ data_loader ─▶ data_cleaning ─▶ analysis / insights    │ ─▶ KPIs, charts, report
            │                     │                                  │
            │                     ▼                                  │
            │               sql_engine (SQLite, read-only)           │
            │                     ▲                                  │
 Question ─▶│ ai_assistant: plan (AI writes SQL/Pandas)              │
            │               execute (APP runs it on the real data)   │
            │               explain (AI explains the actual result)  │
            └─────────────────────────────────────────────────────────┘
```
Only column names, a few example values and query results are sent to OpenAI, never the whole dataset.

## Project Structure
```
AI-Data-Analyst/
├── app.py                  # entry point: navigation + shared sidebar
├── data/sample_sales.csv   # sample dataset
├── src/
│   ├── data_loader.py      # read CSV / Excel
│   ├── data_cleaning.py    # schema detection, column types, quality report, cleaning
│   ├── analysis.py         # profile, KPIs, breakdowns (Pandas)
│   ├── sql_engine.py       # SQLite engine + safe query validation
│   ├── ai_assistant.py     # OpenAI: plan → execute → explain
│   ├── visualization.py    # Plotly charts + automatic chart choice
│   ├── insights.py         # rule-based business insights
│   ├── report.py           # HTML report builder
│   └── ui.py               # sidebar, caching, shared helpers
├── pages/                  # dashboard, data_quality, business_insights, ai_chat, sql_mode, export_report
├── tests/test_core.py      # automated tests (pytest)
├── docs/GUIDE.md           # beginner walkthrough of every file
├── assets/                 # style.css, logo, screenshots
├── requirements.txt
├── .env.example
└── .gitignore
```

## Dataset
`data/sample_sales.csv` is a **synthetic** dataset (25,242 rows) generated in the same format as the [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail): `InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`. It deliberately contains real-world problems (duplicates, cancellations, missing IDs, bad-debt adjustments, extreme quantities) to demonstrate cleaning. The app also works with the real UCI file (541,909 rows) and with other CSV/Excel datasets.

## Data Cleaning
1. Trim column names; convert dates and numbers stored as text
2. Create `Revenue = Quantity × UnitPrice`
3. Flag cancellations (`InvoiceNo` starting with "C" or negative quantity) as `IsCancelled`
4. Remove duplicates, cancellations and zero/negative prices (each optional), logging how many rows each step removed

The cancellation rate is measured *before* removal so it can still be reported.

## SQL Analysis
The cleaned data is loaded into an in-memory SQLite table called `sales`. Example:
```sql
SELECT "Country", ROUND(SUM("Revenue"), 2) AS Revenue
FROM sales
GROUP BY "Country"
ORDER BY Revenue DESC
LIMIT 10;
```
Queries are validated (single `SELECT`/`WITH` statement, no data-changing keywords) and the connection is read-only (`PRAGMA query_only`).

## Python Analysis
Aggregations, grouping, filtering, descriptive statistics, correlations, monthly time series, customer analysis (orders, revenue, AOV per customer) and product trend analysis (first vs second half of the period), e.g.:
```python
df.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
```

## AI Integration
1. **Plan:** the model receives the schema and question and returns JSON with `method` (sql/pandas), `code` and a chart suggestion.
2. **Execute:** the app runs the code: SQL through the read-only engine, Pandas in a restricted namespace on a copy of the data. If it fails, the error is sent back once for self-correction.
3. **Explain:** the model receives only the *calculated result* and returns an answer, calculation, interpretation, recommendation and next question.

Recent conversation turns are included so follow-up questions work.

## Screenshots
_Add screenshots to `assets/screenshots/` and reference them here:_
`![Dashboard](assets/screenshots/dashboard.png)` · `![AI Assistant](assets/screenshots/ai_chat.png)` · `![Data Quality](assets/screenshots/data_quality.png)`

## Example Questions
- What are my top 10 products?
- Which country generates the most revenue? → What was its average order value?
- What was the best sales month?
- Which products have declining sales?
- What percentage of orders were cancelled?
- Give me three important business insights from this dataset.

## Example Insights (sample data)
- Q4 generated 35.2% of annual revenue versus 21.6% for an average other quarter: a strong holiday dependency.
- The United Kingdom accounts for 66.7% of revenue, a concentration risk.
- The top 10% of customers generate 60.6% of identified-customer revenue.

## How to Run Locally
```bash
git clone https://github.com/<your-username>/AI-Data-Analyst.git
cd AI-Data-Analyst
python -m venv venv
venv\Scripts\activate            # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Windows  (Mac/Linux: cp .env.example .env), then add your key
streamlit run app.py
```
Run the tests with `pytest`. The dashboard, data quality, insights, SQL examples and report all work **without** an API key; only the AI features need one.

## Deployment (Streamlit Community Cloud)
Push to GitHub → share.streamlit.io → *New app* → pick the repo and `app.py` → *Advanced settings → Secrets*:
```toml
OPENAI_API_KEY = "sk-..."
```

## Future Improvements
- Support PostgreSQL / cloud warehouses in addition to SQLite
- Customer segmentation (RFM analysis) and simple sales forecasting
- Stronger sandboxing for AI-generated Python (e.g. a separate process)
- User-selected column mapping when automatic detection fails
- PDF export and scheduled reports

## Author
**Austin Chi**: Information Systems & Technology student · Data / Business Analyst
[LinkedIn](#) · [Portfolio](#) · [Email](#)

## Look & auto-arrange

- **Theme** lives in three matching places: `.streamlit/config.toml` (Streamlit widgets), `assets/style.css` (cards, sidebar, pills) and `src/theme.py` (chart colours). Light grey canvas, espresso sidebar, white rounded cards, coral accent.
- **Auto-arrange** (`src/layout.py`): every time a new file is loaded, the dashboard resets its filters, drops any panel the file can't fill (e.g. no country or product column), removes dropdown options the data can't answer, and re-packs the remaining panels two per row at equal height. KPI cards widen to fill the row.
- **Clean screenshot mode** (toggle in the sidebar) hides buttons, expanders, captions and the upload button so the page is ready to capture.
