"""
data_cleaning.py
----------------
Everything about understanding and cleaning the raw data:

1. detect_schema()        -> works out which column is the date, the price, etc.
2. detect_column_types()  -> splits columns into numerical / categorical / date
3. quality_report()       -> finds data problems (missing values, duplicates ...)
4. prepare_data()         -> cleans the data and adds Revenue + IsCancelled
"""

import re
import warnings

import numpy as np
import pandas as pd

# Possible names for each "role" a column can play in a sales dataset.
# Names are compared after lower-casing and removing spaces/underscores,
# so "Invoice Date", "invoice_date" and "InvoiceDate" all match "invoicedate".
ROLE_PATTERNS = {
    "invoice": ["invoiceno", "invoice", "invoiceid", "invoicenumber", "orderid", "orderno",
                "ordernumber", "order", "transactionid", "receiptid"],
    "product_code": ["stockcode", "sku", "productid", "productcode", "itemid", "itemcode"],
    "product": ["description", "productname", "product", "itemname", "item", "productdescription"],
    "quantity": ["quantity", "qty", "units", "unitssold", "quantityordered"],
    "price": ["unitprice", "price", "priceeach", "unitcost", "itemprice"],
    "revenue": ["revenue", "sales", "totalsales", "amount", "totalprice", "linetotal", "salesamount", "total"],
    "date": ["invoicedate", "orderdate", "date", "transactiondate", "saledate", "purchasedate", "timestamp"],
    "customer": ["customerid", "customer", "clientid", "customername", "customerno"],
    "country": ["country", "region", "market", "state"],
}

ROLE_LABELS = {
    "invoice": "Order / invoice ID", "product_code": "Product code", "product": "Product name",
    "quantity": "Quantity", "price": "Unit price", "revenue": "Revenue", "date": "Date",
    "customer": "Customer ID", "country": "Country / region",
}


def _norm(name) -> str:
    """Lower-case a column name and strip anything that is not a letter or digit."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Remove stray spaces around column names (a very common data problem)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_schema(df: pd.DataFrame) -> dict:
    """Match columns to business roles. Returns e.g. {"date": "InvoiceDate", "price": "UnitPrice", ...}."""
    normalised = {_norm(c): c for c in df.columns}
    schema, used = {}, set()
    for role, patterns in ROLE_PATTERNS.items():
        schema[role] = None
        for pattern in patterns:
            col = normalised.get(pattern)
            if col is not None and col not in used:
                schema[role] = col
                used.add(col)
                break
    return schema


def _parse_dates(series: pd.Series) -> pd.Series:
    """Turn text into dates. Values that are not valid dates become NaT (Not a Time)."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(series, errors="coerce")
        # If the quick method failed for many rows, try the slower flexible one.
        if parsed.isna().mean() > series.isna().mean() + 0.05:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    return parsed


def _looks_like_id(col) -> bool:
    n = _norm(col)
    return n.endswith("id") or "code" in n or n in {"invoiceno", "orderno", "zip", "postcode"}


def _looks_like_date(series: pd.Series, col) -> bool:
    sample = series.dropna().astype(str).head(300)
    if sample.empty:
        return False
    name_hint = any(w in _norm(col) for w in ["date", "time", "day", "month", "period"])
    has_separators = sample.str.contains(r"[-/:]").mean() > 0.8
    if not (name_hint or has_separators):
        return False
    return _parse_dates(sample).notna().mean() >= 0.8


def detect_column_types(df: pd.DataFrame) -> dict:
    """Split columns into numerical, categorical and date columns."""
    numerical, categorical, dates = [], [], []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            dates.append(col)
        elif pd.api.types.is_bool_dtype(s):
            categorical.append(col)
        elif pd.api.types.is_numeric_dtype(s):
            # Numbers like CustomerID are labels, not quantities you would add up.
            (categorical if _looks_like_id(col) else numerical).append(col)
        elif _looks_like_date(s, col):
            dates.append(col)
        else:
            categorical.append(col)
    return {"numerical": numerical, "categorical": categorical, "date": dates}


def quality_report(raw: pd.DataFrame, schema: dict, types: dict) -> list[dict]:
    """
    Check the raw data for common problems.
    Each item: check name, count, status ("ok" / "warning"), and what it could mean for the analysis.
    """
    items = []

    def add(check, count, consequence, ok_text="No issues found."):
        items.append({
            "check": check,
            "count": int(count),
            "status": "warning" if count > 0 else "ok",
            "consequence": consequence if count > 0 else ok_text,
        })

    missing = int(raw.isna().sum().sum())
    worst = raw.isna().sum().sort_values(ascending=False)
    worst = worst[worst > 0].head(3)
    detail = ", ".join(f"{c} ({v:,})" for c, v in worst.items())
    add("Missing values", missing,
        f"Most affected columns: {detail}. Rows with gaps can be dropped from some calculations, "
        "so totals and customer counts may be understated.")

    add("Duplicate rows", raw.duplicated().sum(),
        "Exact copies of the same row inflate revenue, order counts and units sold if they are not removed.")

    date_col = schema.get("date") or (types["date"][0] if types["date"] else None)
    if date_col:
        original = raw[date_col]
        parsed = _parse_dates(original)
        add("Invalid dates", (original.notna() & parsed.isna()).sum(),
            "Rows with dates that cannot be read are left out of monthly trends and time-series charts.")

    q, p = schema.get("quantity"), schema.get("price")
    if q:
        qty = pd.to_numeric(raw[q], errors="coerce")
        add("Negative quantities", (qty < 0).sum(),
            "Negative quantities usually mean returns or cancellations. Mixed in with sales, "
            "they reduce revenue and units sold, so they should be analysed separately.")
    if p:
        price = pd.to_numeric(raw[p], errors="coerce")
        add("Negative prices", (price < 0).sum(),
            "Negative prices are often accounting adjustments (e.g. bad-debt write-offs), not real sales.")
        add("Zero prices", (price == 0).sum(),
            "Zero-price lines may be free samples or data-entry errors; they add units but no revenue.")

    extreme_total, extreme_cols = 0, []
    for col in types["numerical"]:
        s = pd.to_numeric(raw[col], errors="coerce").dropna()
        if len(s) < 20:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        n = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum())
        if n:
            extreme_total += n
            extreme_cols.append(f"{col} ({n:,})")
    add("Extreme values", extreme_total,
        f"Values far outside the normal range in: {', '.join(extreme_cols)}. A few very large orders "
        "can distort averages, so medians are worth checking alongside means.")

    wrong_type = []
    for col in raw.columns:
        s = raw[col]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s) or _looks_like_id(col):
            continue  # ID columns (e.g. InvoiceNo) are labels, so text is the right type
        non_null = s.dropna()
        if len(non_null) and pd.to_numeric(non_null, errors="coerce").notna().mean() > 0.95:
            wrong_type.append(col)
    add("Incorrect data types", len(wrong_type),
        f"Columns stored as text but containing numbers: {', '.join(map(str, wrong_type))}. "
        "Text can't be summed or averaged until it is converted.")
    return items


def prepare_data(raw: pd.DataFrame, remove_duplicates=True, remove_cancellations=True,
                 remove_invalid=True):
    """
    Clean the raw data and add helpful columns.

    Returns:
        df     - the cleaned DataFrame used for analysis
        schema - which column plays which role
        log    - a list of plain-English cleaning steps (shown on the Data Quality page)
        meta   - extra numbers measured before cleaning (e.g. cancellation rate)
    """
    df = clean_column_names(raw)
    schema = detect_schema(df)
    log, meta = [], {"rows_before": len(df)}

    # 1. Dates: convert text to real dates so we can group by month.
    if schema["date"]:
        col = schema["date"]
        before = df[col].notna().sum()
        df[col] = _parse_dates(df[col])
        bad = int(before - df[col].notna().sum())
        log.append(f"Converted '{col}' to dates" + (f" ({bad:,} values could not be read)." if bad else "."))

    # Any other column that looks like a date is converted too.
    for col in detect_column_types(df)["date"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = _parse_dates(df[col])
            log.append(f"Converted '{col}' to dates.")
        if schema["date"] is None:
            schema["date"] = col

    # 2. Numbers: make sure quantity and price are numeric.
    for role in ["quantity", "price", "revenue"]:
        col = schema[role]
        if col and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            log.append(f"Converted '{col}' from text to numbers.")

    # 3. Customer IDs like 12346.0 become 12346.
    cust = schema["customer"]
    if cust and pd.api.types.is_float_dtype(df[cust]):
        s = df[cust].dropna()
        if len(s) and (s % 1 == 0).all():
            df[cust] = df[cust].astype("Int64")

    # 4. Revenue = Quantity x UnitPrice
    if schema["quantity"] and schema["price"] and not schema["revenue"]:
        df["Revenue"] = df[schema["quantity"]] * df[schema["price"]]
        schema["revenue"] = "Revenue"
        log.append(f"Created 'Revenue' = {schema['quantity']} × {schema['price']}.")

    # 5. Flag cancellations: invoice numbers starting with "C" or negative quantities.
    inv, qty = schema["invoice"], schema["quantity"]
    if inv or qty:
        flag = pd.Series(False, index=df.index)
        if inv:
            flag |= df[inv].astype(str).str.upper().str.startswith("C")
        if qty:
            flag |= df[qty].fillna(0) < 0
        df["IsCancelled"] = flag
        if inv:
            meta["orders_before"] = int(df[inv].nunique())
            meta["cancelled_orders"] = int(df.loc[flag, inv].nunique())
            if meta["orders_before"]:
                meta["cancel_rate"] = meta["cancelled_orders"] / meta["orders_before"]
        meta["cancelled_rows"] = int(flag.sum())

    # 6. Optional cleaning steps (controlled from the sidebar).
    if remove_duplicates:
        n = int(df.duplicated().sum())
        df = df.drop_duplicates()
        log.append(f"Removed {n:,} duplicate rows.")
    if remove_cancellations and "IsCancelled" in df:
        n = int(df["IsCancelled"].sum())
        df = df[~df["IsCancelled"]]
        log.append(f"Removed {n:,} cancelled / returned rows (analysed separately on the Insights page).")
    if remove_invalid:
        if schema["price"]:
            n = int((df[schema["price"]] <= 0).sum())
            df = df[df[schema["price"]] > 0]
            log.append(f"Removed {n:,} rows with a zero or negative price.")
        if schema["date"]:
            n = int(df[schema["date"]].isna().sum())
            if n:
                df = df[df[schema["date"]].notna()]
                log.append(f"Removed {n:,} rows with a missing or invalid date.")

    df = df.reset_index(drop=True)
    meta["rows_after"] = len(df)
    log.append(f"Rows used for analysis: {len(df):,} of {meta['rows_before']:,}.")
    return df, schema, log, meta
