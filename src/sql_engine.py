"""
sql_engine.py
-------------
Loads the cleaned DataFrame into an in-memory SQLite database
so it can be queried with SQL. The table is always called `sales`.

Safety: only single read-only SELECT queries are allowed, and the
connection itself is switched to read-only (PRAGMA query_only).
"""

import re
import sqlite3

import pandas as pd

TABLE_NAME = "sales"
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex|truncate)\b",
    re.IGNORECASE,
)


class SQLEngine:
    def __init__(self, df: pd.DataFrame, table_name: str = TABLE_NAME):
        self.table_name = table_name
        self.row_count = len(df)
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)

        sql_df = df.copy()
        for col in sql_df.columns:
            if pd.api.types.is_datetime64_any_dtype(sql_df[col]):
                # SQLite has no date type, so dates are stored as text: 'YYYY-MM-DD HH:MM:SS'
                sql_df[col] = sql_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            elif pd.api.types.is_bool_dtype(sql_df[col]):
                sql_df[col] = sql_df[col].astype(int)
        sql_df.to_sql(table_name, self.conn, index=False)
        self.conn.execute("PRAGMA query_only = ON")

    def validate(self, query: str) -> str:
        """Raise ValueError if the query is not a single, read-only SELECT."""
        q = re.sub(r"--[^\n]*", "", query).strip().rstrip(";").strip()
        if not q:
            raise ValueError("The query is empty.")
        if ";" in q:
            raise ValueError("Only one SQL statement can be run at a time.")
        if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
            raise ValueError("Only SELECT queries are allowed in this app.")
        if FORBIDDEN.search(q):
            raise ValueError("This query contains a command that could change the data, so it was blocked.")
        return q

    def run(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(self.validate(query), self.conn)

    def schema_text(self) -> str:
        """Describe the table for people and for the AI: column names and SQL types."""
        info = self.conn.execute(f'PRAGMA table_info("{self.table_name}")').fetchall()
        lines = [f'Table "{self.table_name}" ({self.row_count:,} rows)']
        lines += [f'  "{name}" {ctype}' for _, name, ctype, *_ in info]
        return "\n".join(lines)

    def columns(self) -> list[tuple[str, str]]:
        info = self.conn.execute(f'PRAGMA table_info("{self.table_name}")').fetchall()
        return [(name, ctype) for _, name, ctype, *_ in info]


def example_queries(schema: dict, table: str = TABLE_NAME) -> dict:
    """Ready-made SQL examples built from the detected column names."""
    q = lambda c: f'"{c}"'
    rev, ex = schema.get("revenue"), {}
    if not rev:
        return {"First 10 rows": f"SELECT *\nFROM {table}\nLIMIT 10;"}
    if schema.get("country"):
        ex["Top 10 countries by revenue"] = (
            f"SELECT {q(schema['country'])}, ROUND(SUM({q(rev)}), 2) AS Revenue\nFROM {table}\n"
            f"GROUP BY {q(schema['country'])}\nORDER BY Revenue DESC\nLIMIT 10;")
    if schema.get("product"):
        ex["Top 10 products by revenue"] = (
            f"SELECT {q(schema['product'])}, ROUND(SUM({q(rev)}), 2) AS Revenue\nFROM {table}\n"
            f"GROUP BY {q(schema['product'])}\nORDER BY Revenue DESC\nLIMIT 10;")
    if schema.get("date"):
        ex["Revenue by month"] = (
            f"SELECT strftime('%Y-%m', {q(schema['date'])}) AS Month,\n"
            f"       ROUND(SUM({q(rev)}), 2) AS Revenue\nFROM {table}\nGROUP BY Month\nORDER BY Month;")
    if schema.get("invoice"):
        ex["Average order value"] = (
            f"SELECT ROUND(SUM({q(rev)}) / COUNT(DISTINCT {q(schema['invoice'])}), 2) AS AverageOrderValue\n"
            f"FROM {table};")
    if schema.get("customer") and schema.get("invoice"):
        ex["Most frequent customers"] = (
            f"SELECT {q(schema['customer'])}, COUNT(DISTINCT {q(schema['invoice'])}) AS Orders,\n"
            f"       ROUND(SUM({q(rev)}), 2) AS Revenue\nFROM {table}\nWHERE {q(schema['customer'])} IS NOT NULL\n"
            f"GROUP BY {q(schema['customer'])}\nORDER BY Orders DESC\nLIMIT 10;")
    return ex
