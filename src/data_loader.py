"""
data_loader.py
--------------
Reads a CSV or Excel file and turns it into a Pandas DataFrame
(a table that Python can analyse).
"""

import io
from pathlib import Path

import pandas as pd

# Location of the sample dataset that ships with the project.
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_sales.csv"
SAMPLE_NAME = "sample_sales.csv"


def load_bytes(data: bytes, file_name: str) -> pd.DataFrame:
    """Read raw file bytes into a DataFrame, choosing the reader from the file extension."""
    name = file_name.lower()

    if name.endswith(".csv"):
        try:
            # Most CSV files are saved as UTF-8 text.
            return pd.read_csv(io.BytesIO(data), low_memory=False)
        except UnicodeDecodeError:
            # Some files (like the UCI Online Retail dataset) use an older
            # text format, so we try again with that encoding.
            return pd.read_csv(io.BytesIO(data), encoding="ISO-8859-1", low_memory=False)

    if name.endswith(".xlsx"):
        # openpyxl is the library Pandas uses behind the scenes for Excel.
        return pd.read_excel(io.BytesIO(data), engine="openpyxl")

    raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")


def load_file(uploaded_file) -> pd.DataFrame:
    """Read a file uploaded through Streamlit's file uploader."""
    return load_bytes(uploaded_file.getvalue(), uploaded_file.name)


def load_sample() -> pd.DataFrame:
    """Read the sample sales dataset from the data/ folder."""
    return pd.read_csv(SAMPLE_PATH, low_memory=False)
