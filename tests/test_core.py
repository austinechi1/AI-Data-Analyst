"""
Automated checks for the core logic. Run with:  pytest
Each test builds a tiny dataset where we already know the right answer.
"""

import pandas as pd
import pytest

from src.ai_assistant import run_pandas
from src.analysis import compute_kpis
from src.data_cleaning import detect_schema, prepare_data
from src.sql_engine import SQLEngine


@pytest.fixture
def sales():
    return pd.DataFrame({
        "InvoiceNo": ["1", "1", "2", "C3", "4"],
        "Description": ["Mug", "Plate", "Mug", "Mug", "Mug"],
        "Quantity": [2, 1, 3, -1, 1],
        "UnitPrice": [5.0, 10.0, 5.0, 5.0, 0.0],
        "InvoiceDate": ["2023-01-01", "2023-01-01", "2023-02-01", "2023-02-02", "2023-03-01"],
        "CustomerID": [1, 1, 2, 2, 3],
        "Country": ["UK", "UK", "France", "France", "UK"],
    })


def test_schema_detection(sales):
    schema = detect_schema(sales)
    assert schema["invoice"] == "InvoiceNo"
    assert schema["price"] == "UnitPrice"
    assert schema["date"] == "InvoiceDate"


def test_cleaning_and_revenue(sales):
    df, schema, log, meta = prepare_data(sales)
    # C3 (cancelled) and invoice 4 (zero price) are removed
    assert set(df["InvoiceNo"]) == {"1", "2"}
    assert df["Revenue"].sum() == 2 * 5 + 1 * 10 + 3 * 5
    assert meta["cancelled_orders"] == 1


def test_kpis(sales):
    df, schema, _, _ = prepare_data(sales)
    kpis = compute_kpis(df, schema)
    assert kpis["Total Revenue"] == 35
    assert kpis["Total Orders"] == 2
    assert kpis["Average Order Value"] == 17.5


def test_sql_matches_pandas(sales):
    df, _, _, _ = prepare_data(sales)
    engine = SQLEngine(df)
    sql = engine.run('SELECT "Country", SUM("Revenue") AS Revenue FROM sales GROUP BY "Country" ORDER BY Revenue DESC')
    assert sql.iloc[0]["Country"] == "UK"
    assert sql.iloc[0]["Revenue"] == df.groupby("Country")["Revenue"].sum().max()


@pytest.mark.parametrize("query", ["DROP TABLE sales", "SELECT 1; DELETE FROM sales", "UPDATE sales SET Quantity = 0"])
def test_sql_blocks_changes(sales, query):
    engine = SQLEngine(prepare_data(sales)[0])
    with pytest.raises(ValueError):
        engine.run(query)


def test_pandas_sandbox_blocks_imports(sales):
    with pytest.raises(ValueError):
        run_pandas("import os\nresult = 1", sales)
    assert run_pandas("result = len(df)", sales) == 5
