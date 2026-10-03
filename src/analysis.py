"""
analysis.py
-----------
Pandas calculations: the dataset profile, KPIs and the standard
sales breakdowns (by month, country, product and customer).
Every number shown in the app comes from a function in this file,
from SQL (sql_engine.py) or from code the AI writes and the app runs.
"""

import numpy as np
import pandas as pd


def profile_dataset(raw: pd.DataFrame, types: dict) -> dict:
    """Basic facts about the uploaded file, before any cleaning."""
    dtypes = pd.DataFrame({
        "Column": raw.columns,
        "Data type": [str(t) for t in raw.dtypes],
        "Missing": raw.isna().sum().values,
        "Unique values": raw.nunique().values,
    })
    return {
        "rows": len(raw),
        "columns": raw.shape[1],
        "missing_values": int(raw.isna().sum().sum()),
        "duplicate_rows": int(raw.duplicated().sum()),
        "numerical": types["numerical"],
        "categorical": types["categorical"],
        "date": types["date"],
        "dtypes": dtypes,
    }


def is_sales_data(schema: dict) -> bool:
    return bool(schema.get("revenue"))


def compute_kpis(df: pd.DataFrame, schema: dict) -> dict:
    """Headline business numbers. Only KPIs the data supports are returned."""
    kpis = {}
    rev, inv, cust, qty = schema.get("revenue"), schema.get("invoice"), schema.get("customer"), schema.get("quantity")
    if rev:
        kpis["Total Revenue"] = float(df[rev].sum())
    if inv:
        kpis["Total Orders"] = int(df[inv].nunique())
    if cust:
        kpis["Total Customers"] = int(df[cust].nunique())
    if rev and inv and kpis.get("Total Orders"):
        kpis["Average Order Value"] = kpis["Total Revenue"] / kpis["Total Orders"]
    if qty:
        kpis["Total Units Sold"] = float(df[qty].sum())
    if qty and inv and kpis.get("Total Orders"):
        kpis["Average Units per Order"] = kpis["Total Units Sold"] / kpis["Total Orders"]
    return kpis


def format_kpi(name: str, value: float) -> str:
    if name in ("Total Revenue", "Average Order Value"):
        return f"£{value:,.2f}" if value < 1000 else f"£{value:,.0f}"
    if name == "Average Units per Order":
        return f"{value:,.1f}"
    return f"{value:,.0f}"


def revenue_over_time(df: pd.DataFrame, schema: dict, freq: str = "MS") -> pd.DataFrame:
    """Revenue and order count per month (freq="MS"), week ("W") or day ("D")."""
    date, rev, inv = schema["date"], schema["revenue"], schema.get("invoice")
    grouped = df.groupby(pd.Grouper(key=date, freq=freq))
    out = grouped[rev].sum().rename("Revenue").to_frame()
    if inv:
        out["Orders"] = grouped[inv].nunique()
    out = out.reset_index().rename(columns={date: "Period"})
    return out[out["Revenue"] != 0]


def top_n_by(df: pd.DataFrame, group_col: str, value_col: str, n: int = 10) -> pd.DataFrame:
    """Sum value_col for each group and return the top n groups."""
    out = (df.groupby(group_col, dropna=True)[value_col].sum()
             .sort_values(ascending=False).head(n).reset_index())
    return out


def revenue_share(df: pd.DataFrame, group_col: str, rev: str) -> pd.DataFrame:
    out = df.groupby(group_col)[rev].sum().sort_values(ascending=False).reset_index()
    out["Share %"] = out[rev] / out[rev].sum() * 100
    return out


def customer_summary(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """One row per customer: number of orders, revenue and average order value."""
    cust, inv, rev = schema["customer"], schema["invoice"], schema["revenue"]
    out = df.dropna(subset=[cust]).groupby(cust).agg(Orders=(inv, "nunique"), Revenue=(rev, "sum"))
    out["Average Order Value"] = out["Revenue"] / out["Orders"]
    return out.sort_values("Orders", ascending=False).reset_index()


def order_values(df: pd.DataFrame, schema: dict) -> pd.Series:
    """Total value of each order (used for the order-value histogram)."""
    return df.groupby(schema["invoice"])[schema["revenue"]].sum().rename("Order Value")


def product_trends(df: pd.DataFrame, schema: dict, min_revenue_share: float = 0.005) -> pd.DataFrame:
    """
    Compare each product's revenue in the first half of the date range
    with the second half. Negative change = declining sales.
    """
    date, rev = schema["date"], schema["revenue"]
    prod = schema.get("product") or schema.get("product_code")
    midpoint = df[date].min() + (df[date].max() - df[date].min()) / 2
    first = df[df[date] < midpoint].groupby(prod)[rev].sum()
    second = df[df[date] >= midpoint].groupby(prod)[rev].sum()
    out = pd.DataFrame({"First half": first, "Second half": second}).fillna(0)
    out = out[(out.sum(axis=1) / out.values.sum()) >= min_revenue_share]
    out["Change %"] = np.where(out["First half"] > 0,
                               (out["Second half"] - out["First half"]) / out["First half"] * 100, np.nan)
    return out.sort_values("Change %").reset_index().rename(columns={prod: "Product"})


def numeric_summary(df: pd.DataFrame, numerical: list) -> pd.DataFrame:
    """Descriptive statistics: count, mean, std, min, quartiles, max."""
    if not numerical:
        return pd.DataFrame()
    return df[numerical].describe().T.round(2)


def correlation_matrix(df: pd.DataFrame, numerical: list) -> pd.DataFrame:
    cols = [c for c in numerical if df[c].nunique() > 1]
    return df[cols].corr().round(2) if len(cols) >= 2 else pd.DataFrame()


# ---------------------------------------------------------------- dashboard filters
def period_options(df: pd.DataFrame, date_col: str) -> dict:
    """
    Date-range choices for the dashboard filter.
    Each option is (first month, number of months), e.g. ("2023-10", 3) for Q4 2023.
    """
    months = df[date_col].dropna().dt.to_period("M")
    if months.empty:
        return {}
    first, last = months.min(), months.max()
    total = (last - first).n + 1
    options = {f"{first.strftime('%b %Y')} – {last.strftime('%b %Y')}": (first, total)}
    if total > 3:
        options["Last 3 months"] = (last - 2, 3)
    if total > 6:
        options["Last 6 months"] = (last - 5, 6)
    for q in sorted(months.dt.asfreq("Q").unique(), reverse=True):
        options[f"Q{q.quarter} {q.year}"] = (q.asfreq("M", how="start"), 3)
    return options


def filter_months(df: pd.DataFrame, date_col: str, start, n_months: int) -> pd.DataFrame:
    months = df[date_col].dt.to_period("M")
    return df[(months >= start) & (months <= start + (n_months - 1))]


def previous_period(df: pd.DataFrame, date_col: str, start, n_months: int):
    """The same number of months just before `start`, or None if the data doesn't go back that far."""
    first = df[date_col].dropna().dt.to_period("M").min()
    prev_start = start - n_months
    if prev_start < first:
        return None
    return filter_months(df, date_col, prev_start, n_months)


def kpi_trends(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Revenue, orders, customers and average order value per month (or per week for short periods)."""
    date, rev, inv, cust = schema["date"], schema["revenue"], schema.get("invoice"), schema.get("customer")
    span_days = (df[date].max() - df[date].min()).days if len(df) else 0
    freq = "W" if span_days <= 100 else "MS"
    g = df.groupby(pd.Grouper(key=date, freq=freq))
    out = pd.DataFrame({"Revenue": g[rev].sum()})
    if inv:
        out["Orders"] = g[inv].nunique()
        out["AOV"] = out["Revenue"] / out["Orders"].replace(0, np.nan)
    if cust:
        out["Customers"] = g[cust].nunique()
    return out[out["Revenue"] != 0]


def pct_change(current: float, previous: float | None):
    if previous in (None, 0) or previous != previous:
        return None
    return (current - previous) / abs(previous)
