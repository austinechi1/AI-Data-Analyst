# Beginner's Guide: How This Project Works

This guide walks through every part of the project in plain language. For each file you'll find:
**what it does · why we need it · where it belongs · how to test it · what you should see.**

Read it in order. It follows the same stages as the original project plan.

---

## Before you start: three ideas you need

**DataFrame.** Pandas' version of a spreadsheet table: rows and columns in Python. Almost everything in this project takes a DataFrame in and gives a DataFrame (or a number) back.

**Streamlit reruns.** Every time you click something, Streamlit runs the page script again from top to bottom. To stop it re-reading a big file on every click, we *cache* results with `@st.cache_data` and `@st.cache_resource`: "remember this answer unless the input changes".

**Session state.** `st.session_state` is a dictionary that survives those reruns. We keep the loaded dataset and the chat history in it.

---

## Stage 1: The app shell · `app.py`
- **What:** sets the page title and layout, lists the pages (`st.navigation`) and draws the sidebar.
- **Why:** Streamlit needs one starting file. Keeping it short makes the structure easy to follow.
- **Where:** project root.
- **Test:** `streamlit run app.py`
- **Expected:** a dark copper-themed welcome screen with a *Try the sample sales dataset* button, an **Upload Dataset** button top right, and the page menu in the sidebar.

## Stages 2–3: Uploading CSV and Excel · `src/data_loader.py`
- **What:** `load_bytes()` looks at the file extension and uses `pd.read_csv` or `pd.read_excel`. If a CSV isn't UTF-8, it retries with `ISO-8859-1` (the real UCI file needs this).
- **Why:** file reading lives in one place, so pages never worry about formats.
- **Where:** `src/`.
- **Test:** upload `data/sample_sales.csv`, then save it as .xlsx in Excel and upload that.
- **Expected:** both load, and the header shows the file name and row count; the sidebar card says **Dataset Ready**.

## Stage 4: Profiling · `src/data_cleaning.py` + `src/analysis.py`
- **What:**
  - `detect_column_types()` sorts columns into numerical, categorical and date. ID columns like `CustomerID` are numbers but count as categorical, because adding up IDs makes no sense.
  - `detect_schema()` matches column names to business roles (price, quantity, date...) so the app works even if a file says `Unit Price` instead of `UnitPrice`.
  - `profile_dataset()` counts rows, missing values and duplicates.
- **Why:** an analyst always understands the data before answering questions.
- **Test:** open **Dashboard** → *Dataset profile*.
- **Expected:** Date: InvoiceDate · Numerical: Quantity, UnitPrice · Categorical: InvoiceNo, StockCode, Description, CustomerID, Country.

## Data quality and cleaning · `src/data_cleaning.py`
- **What:**
  - `quality_report()` checks the *raw* data for each problem in the brief and explains the business consequence of each.
  - `prepare_data()` cleans it and creates two new columns: `Revenue` and `IsCancelled`.
- **Why:** dirty data gives wrong answers. Cancellations, for example, would make revenue look lower than it really is.
- **Test:** open **Data Quality**. Then untick *Remove duplicate rows* in the sidebar's *Cleaning options*.
- **Expected:** 120 duplicate rows and 444 negative quantities are found. Unticking the option changes "Rows after cleaning".

## Stage 5: KPIs · `src/analysis.py → compute_kpis()`
- **What:** total revenue, orders (unique invoices), customers, average order value (revenue ÷ orders), units, and units per order.
- **Why:** these are the first numbers any manager asks for.
- **Test:** look at the **Key metrics** cards on the Dashboard.
- **Expected (sample data, default cleaning):** revenue ≈ £814,830, 4,122 orders, 609 customers, AOV ≈ £197.68.

## Stage 6: Charts · `src/visualization.py`
- **What:** one function per chart type, all styled the same. `auto_chart()` looks at a result table and picks a chart: a time column means a line chart, categories mean bars, a single number means no chart.
- **Why:** the AI and SQL pages can then show a sensible chart for *any* result.
- **Test:** click through the Dashboard chart tabs.
- **Expected:** a monthly line that peaks in Q4, the UK as the tallest country bar, and REGENCY CAKESTAND 3 TIER as the top product.

## Stage 7: SQLite · `src/sql_engine.py`
- **What:** copies the cleaned DataFrame into an in-memory SQLite table called `sales`. `validate()` only lets through a single `SELECT`, and the connection is set to read-only.
- **Why:** it shows real SQL skills, and it's safe to run AI-written SQL.
- **Test:** **SQL Mode** → pick *Revenue by month* → *Use example*. Then try `DELETE FROM sales` and click *Run query*.
- **Expected:** 12 monthly rows plus a chart. The DELETE shows "Only SELECT queries are allowed".

## Stage 8: Natural language → SQL · `ai_assistant.nl_to_sql()`
- **What:** sends the table's column list plus your question to OpenAI and gets back a SQL query, which appears in the editor *before* it runs.
- **Why:** the user sees exactly what was calculated. There's no black box.
- **Test (needs API key):** type *Show me the top 10 countries by revenue* and click *Generate SQL*.
- **Expected:** a `SELECT ... GROUP BY "Country" ORDER BY ... LIMIT 10` query, a result table, a bar chart and an *Explain this result* button.

## Stages 9–11: AI assistant and follow-ups · `src/ai_assistant.py` + `pages/ai_chat.py`
- **What:** `ask()` runs three steps:
  1. **Plan:** the AI writes SQL or Pandas code.
  2. **Execute:** *the app* runs it on the real data. If it errors, the AI gets one chance to fix it.
  3. **Explain:** the AI sees only the actual result and returns an answer, calculation, interpretation, recommendation and next question.

  The last 6 questions and answers are sent along, so "its" in a follow-up refers to the right thing.
- **Why:** this is how the brief's rule "the AI must NOT simply guess answers" is enforced.
- **Test:** ask *Which country had the highest revenue?*, then *What was its average order value?*
- **Expected:** the first answer is the United Kingdom. The second calculates the UK's AOV. Open *How this was calculated* to see the code.

**Safety note:** AI-written Pandas runs with no imports, no file access, and only on a copy of the data. This is a sensible portfolio-level guard, not a full sandbox. It's mentioned under Future Improvements in the README.

## Stage 10: Business insights · `src/insights.py`
- **What:** calculates insights with rules (best month, Q4 share, market concentration, top product, declining products, customer concentration, cancellation rate). Each one comes with a "why it matters". The optional AI button turns these facts into recommendations, but it is never allowed to invent numbers.
- **Test:** open **Business Insights**.
- **Expected:** for example "Q4 generated 35.2% of revenue" and "United Kingdom ... 66.7% of total revenue".

## Stage 12: Report · `src/report.py` + `pages/export_report.py`
- **What:** builds one HTML file containing the overview, KPIs, quality report, cleaning steps, charts, findings and recommendations.
- **Test:** **Analysis Report** → *Generate Analysis Report*, then open the downloaded file.
- **Expected:** a styled report. Press Ctrl + P → Save as PDF for a PDF copy.

## Stage 13: UI · `src/ui.py`, `src/theme.py`, `src/icons.py`, `assets/style.css`, `.streamlit/config.toml`
- **What:** the dark copper theme. `config.toml` sets the base colours and font, `style.css` styles the cards and menu, `theme.py` holds the colour codes the charts use, and `icons.py` draws the small line icons.
- **Dashboard extras:** period and country filters, KPI cards with sparklines and "vs previous period" changes (shown when the data goes back far enough, e.g. pick *Q4 2023*), and a Business Summary that is calculated by default and can be rewritten by AI with *Write with AI*.
- **Test:** pick *Q4 2023* in the period filter.
- **Expected:** Total Revenue £286,753 with ▲ +40.3% vs. previous 3 months.

---

## Setting up your OpenAI key
1. Get a key at platform.openai.com → API keys. You need to add a small amount of credit to your account.
2. In VS Code, right-click `.env.example` → Copy, then right-click the project folder → Paste.
3. Rename the copy to exactly `.env`.
4. Replace `your_key_here` with your key and save.
5. Stop the app (Ctrl + C) and run `streamlit run app.py` again.

The sidebar should now say *AI assistant: connected*. `.env` is listed in `.gitignore`, so it is never uploaded to GitHub.

## Running the tests
In the terminal, with `(venv)` showing, run `pytest`. Expected result: **8 passed**. Each test uses a tiny table where the right answer is known in advance (e.g. AOV must be exactly 17.5).

## Stage 14: Deploy
1. Push the project to GitHub (next section).
2. Go to share.streamlit.io and sign in with GitHub.
3. Choose *Create app*, select the repo, and set the main file to `app.py`.
4. Under *Advanced settings → Secrets*, add `OPENAI_API_KEY = "sk-..."`.
5. Click *Deploy*.

## Stage 15: GitHub
```bash
git init
git add .
git commit -m "AI Data Analyst: full application"
git branch -M main
git remote add origin https://github.com/<your-username>/AI-Data-Analyst.git
git push -u origin main
```
Before pushing, run `git status` and check that `.env` is **not** in the list.
