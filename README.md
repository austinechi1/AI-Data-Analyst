# AI Data Analyst — Ask Your Data

> **An AI-assisted analytics application that turns uploaded CSV/Excel data into traceable KPIs, SQL analysis, visualizations, and business insights.**

**Portfolio focus:** AI-assisted analytics · Python · SQL · Data Quality · Business Intelligence

[![Python](https://img.shields.io/badge/Python-Analysis-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/SQLite-SQL-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-Visualization-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/)

## Executive Summary

Many small and mid-sized businesses have useful operational data but lack a fast, reliable way to turn it into answers.

**AI Data Analyst** addresses that gap with a Streamlit application where a user can upload a CSV or Excel file, inspect data quality, generate KPIs and charts, ask questions in natural language, and receive business-oriented explanations.

The key design principle is:

> **AI-assisted, not AI-replaced.**

The AI proposes SQL or Python analysis, but the application executes the analysis on the user's data and exposes the generated logic. This keeps the analytical result traceable rather than treating the AI response as the source of truth.

## Business Problem

Business users often need answers such as:

- Which country generates the most revenue?
- What products are driving sales?
- Which month performed best?
- What percentage of orders were cancelled?
- Which customers contribute the most revenue?

Traditional spreadsheets can make these questions time-consuming, while a generic AI chatbot may produce numbers that cannot easily be verified.

This project combines **data profiling, cleaning, deterministic calculations, SQL, visualization, and AI assistance** into one workflow.

## What the Application Does

| Capability | Business value |
|---|---|
| CSV/Excel upload | Analyse a dataset without rebuilding a dashboard |
| Data profiling | Understand schema, types, missing values and duplicates |
| Data-quality checks | Identify issues before analysis |
| Cleaning controls | Make cleaning decisions explicit and measurable |
| KPI dashboard | Quickly assess revenue, orders, customers and units |
| SQL mode | Explore data with transparent SQL |
| Natural-language SQL | Ask analytical questions without writing SQL manually |
| AI assistant | Ask follow-up questions and receive result-backed explanations |
| Business insights | Separate calculated facts from interpretation and recommendations |
| HTML report | Package findings for sharing |

## Analytics Workflow

**Upload → Profile → Validate → Clean → Analyse → Visualize → Interpret → Recommend**

The application is designed around a simple analytical principle:

**The data produces the number. The AI helps explain the number.**

## Technology Stack

| Layer | Technology |
|---|---|
| Programming | Python |
| Data manipulation | Pandas, NumPy |
| SQL engine | SQLite |
| Visualization | Plotly |
| Application | Streamlit |
| AI | OpenAI API |
| Configuration | python-dotenv |
| Testing | pytest |
| Version control | Git/GitHub |

## Architecture

```text
                         ┌──────────────────────────┐
                         │      Streamlit UI        │
                         │ app.py + pages/          │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │       Data Loader         │
                         │     CSV / Excel           │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │     Data Cleaning         │
                         │ profiling + validation    │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┴──────────────────┐
                    │                                    │
          ┌─────────▼─────────┐                ┌─────────▼─────────┐
          │ Python Analysis   │                │   SQLite SQL      │
          │ KPIs + statistics │                │ safe read-only    │
          └─────────┬─────────┘                └─────────┬─────────┘
                    │                                    │
                    └────────────────┬───────────────────┘
                                     │
                            ┌────────▼────────┐
                            │ Charts + Insights│
                            └────────┬─────────┘
                                     │
                            ┌────────▼─────────┐
                            │  AI Assistant     │
                            │ plan → execute    │
                            │ → explain         │
                            └───────────────────┘
```

Only schema information, limited example values, and calculated query results are sent to the OpenAI API; the application does not send the entire dataset.

## Dataset

The included `data/sample_sales.csv` is a **synthetic 25,242-row dataset** following the structure of the UCI Online Retail dataset:

`InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`

It deliberately contains realistic data-quality issues such as duplicates, cancellations, missing customer IDs, extreme quantities, and invalid prices.

The application can also work with other compatible CSV/Excel datasets.

## Data Quality & Cleaning

The application checks for:

- Missing values
- Duplicate records
- Invalid dates
- Negative quantities
- Zero or negative prices
- Extreme values
- Incorrect data types
- Cancellation/return records

A calculated `Revenue` field is created as:

`Revenue = Quantity × UnitPrice`

Cleaning operations are configurable so the user can see what was removed and why.

## SQL Analysis

Cleaned data is loaded into an in-memory SQLite table named `sales`.

Example:

```sql
SELECT
    "Country",
    ROUND(SUM("Revenue"), 2) AS Revenue
FROM sales
GROUP BY "Country"
ORDER BY Revenue DESC
LIMIT 10;
```

The SQL engine validates queries and permits read-only `SELECT` / `WITH` statements.

## Python Analysis

Pandas is used for:

- Grouped analysis
- Descriptive statistics
- Customer analysis
- Product analysis
- Monthly trends
- Correlations
- KPI calculations

Example:

```python
df.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
```

## AI Analysis Flow

The AI workflow follows three stages:

### 1. Plan
The model receives the dataset schema and the user's question and proposes an analytical method.

### 2. Execute
The application executes the proposed SQL or Pandas analysis against the actual dataset.

### 3. Explain
The AI receives the **calculated result**, then produces an interpretation, recommendation, and possible next question.

This separation is important because the AI does not simply invent a business answer independently of the data.

## Example Business Questions

- What are the top 10 products by revenue?
- Which country generates the most revenue?
- What was the best sales month?
- Which products have declining sales?
- What percentage of orders were cancelled?
- What are three important business insights from this dataset?
- What was the average order value for the highest-revenue country?

## Example Insights

Using the included sample data, the application can surface findings such as:

- Q4 generated a disproportionately large share of annual revenue, indicating seasonal demand.
- The United Kingdom represents a major share of revenue, indicating geographic concentration.
- A relatively small group of high-value customers contributes a large share of identified-customer revenue.

These examples demonstrate the type of analysis the application can produce; results depend on the uploaded dataset and selected cleaning rules.

## Project Structure

```text
AI-Data-Analyst/
├── app.py
├── data/
│   └── sample_sales.csv
├── src/
│   ├── data_loader.py
│   ├── data_cleaning.py
│   ├── analysis.py
│   ├── sql_engine.py
│   ├── ai_assistant.py
│   ├── visualization.py
│   ├── insights.py
│   ├── report.py
│   └── ui.py
├── pages/
│   ├── dashboard
│   ├── data_quality
│   ├── business_insights
│   ├── ai_chat
│   ├── sql_mode
│   └── export_report
├── tests/
│   └── test_core.py
├── docs/
│   └── GUIDE.md
├── assets/
├── requirements.txt
├── .env.example
└── .gitignore
```

## Running Locally

```bash
git clone https://github.com/austinechi1/AI-Data-Analyst.git
cd AI-Data-Analyst

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file from `.env.example` and add your OpenAI API key if you want to use the AI features.

Then run:

```bash
streamlit run app.py
```

Run tests with:

```bash
pytest
```

The core dashboard and analytical functionality can run without an API key; the AI features require one.

## Deployment

The application can be deployed using **Streamlit Community Cloud**.

Configure the required secret:

```toml
OPENAI_API_KEY = "your-key"
```

## Key Skills Demonstrated

**Data Analytics:** data cleaning · profiling · KPI development · exploratory analysis · business insights

**SQL:** SQLite · aggregation · filtering · grouping · analytical queries · safe query execution

**Python:** Pandas · NumPy · reusable modules · data transformation

**Visualization:** Plotly · interactive dashboards · KPI storytelling

**AI:** natural-language analytics · SQL generation · result-backed explanations

**Engineering:** Streamlit · testing · modular architecture · Git/GitHub

## Future Improvements

- PostgreSQL/cloud warehouse support
- RFM customer segmentation
- Forecasting
- Stronger sandboxing for AI-generated Python
- Automated scheduled reports
- PDF export
- Role-based access
- Audit logging

## Author

**Nwachukwu Austine**  
Data Analyst | SQL | Python | Power BI

[GitHub](https://github.com/austinechi1) · [Portfolio](https://austinechi1.github.io/) · [Email](mailto:austinechi.fx@gmail.com)

---

<p align="center"><strong>AI-assisted analytics. Traceable numbers. Better decisions.</strong></p>
