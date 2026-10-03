"""
insights.py
-----------
Rule-based business insights. Every insight has three parts:
  fact  - a number calculated from the data (no AI involved)
  why   - why a business should care
  title - a short headline
The AI can later turn these facts into recommendations, but the facts
themselves always come from Pandas, so they can be checked.
"""

import pandas as pd

from src.analysis import customer_summary, product_trends, revenue_over_time


def _money(x):
    return f"£{x:,.0f}"


def generate_insights(df: pd.DataFrame, schema: dict, meta: dict) -> list[dict]:
    rev = schema.get("revenue")
    if not rev or df.empty:
        return generic_insights(df)
    total = df[rev].sum()
    insights = []

    def add(title, fact, why):
        insights.append({"title": title, "fact": fact, "why": why})

    # Time: best month, Q4 effect, latest month-over-month change
    if schema.get("date"):
        monthly = revenue_over_time(df, schema)
        if len(monthly) >= 2:
            best = monthly.loc[monthly["Revenue"].idxmax()]
            add("Best sales month",
                f"{best['Period']:%B %Y} was the strongest month with {_money(best['Revenue'])} in revenue "
                f"({best['Revenue'] / total:.1%} of the total).",
                "Knowing the peak month helps plan stock, staffing and marketing spend ahead of time.")

            quarters = df.groupby(df[schema["date"]].dt.quarter)[rev].sum()
            if len(quarters) == 4 and quarters.idxmax() == 4:
                add("Revenue peaks in Q4",
                    f"Q4 (Oct–Dec) generated {_money(quarters[4])}, {quarters[4] / quarters.sum():.1%} of revenue, "
                    f"compared with {quarters[[1, 2, 3]].mean() / quarters.sum():.1%} for an average other quarter.",
                    "Heavy reliance on the holiday season is a risk: a weak Q4 would hurt the whole year. "
                    "It also shows where promotions get the biggest return.")

            last, prev = monthly.iloc[-1], monthly.iloc[-2]
            last_day = df[schema["date"]].max()
            partial = last_day.day < 25 and last_day.to_period("M") == last["Period"].to_period("M")
            change = (last["Revenue"] - prev["Revenue"]) / prev["Revenue"] if prev["Revenue"] else 0
            fact = (f"Revenue in {last['Period']:%B %Y} was {_money(last['Revenue'])}, "
                    f"{abs(change):.1%} {'higher' if change >= 0 else 'lower'} than {prev['Period']:%B %Y}.")
            if partial:
                fact += f" Note: data for {last['Period']:%B} only runs to day {last_day.day}, so the month is incomplete."
            add("Latest month vs previous month", fact,
                "Month-on-month change is an early warning signal. A partial month can look like a drop, "
                "so always check the date coverage before reacting.")

    # Geography
    if schema.get("country"):
        by_country = df.groupby(schema["country"])[rev].sum().sort_values(ascending=False)
        top, share = by_country.index[0], by_country.iloc[0] / total
        add("Revenue is concentrated in one market" if share > 0.5 else "Top market",
            f"{top} generated {_money(by_country.iloc[0])}, {share:.1%} of total revenue, "
            f"across {len(by_country)} countries in the data.",
            "When most revenue comes from one country, the business is exposed to that market's economy, "
            "regulation and currency. Growing the next markets reduces that risk.")

        if schema.get("invoice"):
            g = df.groupby(schema["country"]).agg(Revenue=(rev, "sum"), Orders=(schema["invoice"], "nunique"))
            g = g[g["Orders"] >= 20]
            if len(g) >= 2:
                g["AOV"] = g["Revenue"] / g["Orders"]
                best = g["AOV"].idxmax()
                overall = total / df[schema["invoice"]].nunique()
                add("Highest average order value by country",
                    f"Customers in {best} spend {_money(g.loc[best, 'AOV'])} per order on average, "
                    f"versus {_money(overall)} across all orders (countries with 20+ orders).",
                    "High-value markets can justify more targeted marketing or dedicated account management.")

    # Products
    prod = schema.get("product") or schema.get("product_code")
    if prod:
        by_prod = df.groupby(prod)[rev].sum().sort_values(ascending=False)
        add("Top product",
            f"'{by_prod.index[0]}' is the top product with {_money(by_prod.iloc[0])} "
            f"({by_prod.iloc[0] / total:.1%} of revenue). The top 5 products make up "
            f"{by_prod.head(5).sum() / total:.1%}.",
            "Best-sellers should never go out of stock, and their performance drives overall results.")
        if schema.get("date"):
            trends = product_trends(df, schema).dropna(subset=["Change %"])
            declining = trends[trends["Change %"] < -20]
            if not declining.empty:
                worst = declining.iloc[0]
                add("Products with declining sales",
                    f"{len(declining)} products sold at least 20% less in the second half of the period. "
                    f"The biggest fall: '{worst['Product']}' ({worst['Change %']:.0f}%).",
                    "Declining products may need a price review, a promotion, or to be phased out "
                    "to free up stock space for growing lines.")

    # Customers
    if schema.get("customer") and schema.get("invoice"):
        cs = customer_summary(df, schema)
        if len(cs) >= 10:
            top_n = max(1, int(len(cs) * 0.1))
            share = cs.nlargest(top_n, "Revenue")["Revenue"].sum() / cs["Revenue"].sum()
            repeat = (cs["Orders"] > 1).mean()
            add("Customer concentration",
                f"The top 10% of customers ({top_n:,} people) generate {share:.1%} of revenue from identified "
                f"customers. {repeat:.1%} of customers ordered more than once.",
                "Keeping a small group of high-value customers happy protects a large part of revenue; "
                "a loyalty programme or personal outreach is often worth it.")

    # Cancellations (measured before cleaning removed them)
    if meta.get("cancel_rate") is not None:
        add("Cancelled orders",
            f"{meta['cancelled_orders']:,} of {meta['orders_before']:,} orders ({meta['cancel_rate']:.1%}) "
            "were cancelled or returned.",
            "Cancellations cost money twice: lost revenue and handling costs. Finding which products or "
            "customers cancel most often points to quality or expectation problems.")
    return insights


def generic_insights(df: pd.DataFrame) -> list[dict]:
    """Fallback insights for datasets that are not sales data."""
    insights = []
    missing = df.isna().mean().sort_values(ascending=False)
    if len(missing) and missing.iloc[0] > 0:
        insights.append({"title": "Most incomplete column",
                         "fact": f"'{missing.index[0]}' is missing {missing.iloc[0]:.1%} of its values.",
                         "why": "Conclusions that rely on this column are based on less data than the others."})
    num = df.select_dtypes("number")
    num = num.loc[:, num.nunique() > 1]
    if num.shape[1] >= 2:
        corr = num.corr().abs()
        for c in corr.columns:
            corr.loc[c, c] = 0
        a, b = corr.stack().idxmax()
        insights.append({"title": "Strongest relationship",
                         "fact": f"'{a}' and '{b}' have the strongest correlation ({num[a].corr(num[b]):.2f}).",
                         "why": "Correlated measures move together. It is a lead to investigate, not proof of cause."})
    cat = df.select_dtypes(exclude="number")
    for col in cat.columns[:2]:
        vc = df[col].value_counts()
        if 1 < len(vc) < len(df) * 0.5:
            insights.append({"title": f"Most common {col}",
                             "fact": f"'{vc.index[0]}' appears in {vc.iloc[0] / vc.sum():.1%} of rows.",
                             "why": "The most common category usually dominates totals, so check it first."})
    return insights


def dashboard_highlights(df: pd.DataFrame, schema: dict) -> list[dict]:
    """Three short, calculated highlights for the dashboard's Business Summary panel."""
    rev = schema.get("revenue")
    if not rev or df.empty:
        return []
    total = df[rev].sum()
    items = []

    # 1. Trend over the selected period
    if schema.get("date"):
        monthly = revenue_over_time(df, schema)
        if len(monthly) >= 2:
            best = monthly.loc[monthly["Revenue"].idxmax()]
            first, last = monthly.iloc[0], monthly.iloc[-1]
            if best["Period"] == first["Period"]:
                # The best month is the first one, so describe what happened after it.
                change = (last["Revenue"] - best["Revenue"]) / best["Revenue"]
                items.append({"icon": "trend", "title": f"Peak in {best['Period']:%B}",
                              "text": f"Revenue peaked at {_money(best['Revenue'])} in {best['Period']:%B %Y}; "
                                      f"{last['Period']:%B} closed at {_money(last['Revenue'])} ({change:+.0%})."})
            else:
                growth = (best["Revenue"] - first["Revenue"]) / first["Revenue"] if first["Revenue"] else 0
                title = f"Strong growth into {best['Period']:%B}" if growth >= 0.25 else f"Peak in {best['Period']:%B}"
                items.append({"icon": "trend", "title": title,
                              "text": f"Revenue peaked at {_money(best['Revenue'])} in {best['Period']:%B %Y}, "
                                      f"{growth:+.0%} versus {first['Period']:%B} ({_money(first['Revenue'])})."})

    # 2. Geography (or customers, when one country is selected)
    country = schema.get("country")
    if country and df[country].nunique() > 1:
        by = df.groupby(country)[rev].sum().sort_values(ascending=False) / total
        others = ", ".join(f"{c} ({s:.1%})" for c, s in by.iloc[1:3].items())
        title = f"{by.index[0]} dominates" if by.iloc[0] > 0.5 else f"{by.index[0]} leads"
        items.append({"icon": "bars", "title": title,
                      "text": f"{by.index[0]} accounts for {by.iloc[0]:.1%} of revenue "
                              f"({_money(by.iloc[0] * total)}), ahead of {others}."})
    elif schema.get("customer") and schema.get("invoice"):
        cs = customer_summary(df, schema)
        if len(cs) >= 10:
            top_n = max(1, int(len(cs) * 0.1))
            share = cs.nlargest(top_n, "Revenue")["Revenue"].sum() / cs["Revenue"].sum()
            items.append({"icon": "users", "title": "Loyal customers matter",
                          "text": f"The top 10% of customers ({top_n:,}) bring in {share:.1%} of revenue "
                                  f"from {len(cs):,} identified customers."})

    # 3. Products
    prod = schema.get("product") or schema.get("product_code")
    if prod:
        by_prod = df.groupby(prod)[rev].sum().sort_values(ascending=False)
        items.append({"icon": "cart", "title": "Top products drive revenue",
                      "text": f"The top 3 products contribute {by_prod.head(3).sum() / total:.0%} of revenue, "
                              f"led by {str(by_prod.index[0]).title()} ({_money(by_prod.iloc[0])})."})
    return items
