"""
Shared utilities for PDF statement extraction.
Common functions used across all bank extractors.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import pdfplumber
import pandas as pd


def get_password_from_filename(filepath: str) -> str:
    """Extract password from filename (last segment after '_').

    Args:
        filepath: Path to the PDF file

    Returns:
        Password string extracted from filename, or empty string if not found
    """
    filename = Path(filepath).stem
    parts = filename.split('_')
    return parts[-1] if parts else ""


def open_pdf(pdf_path: str, password: Optional[str] = None):
    """Open PDF, handling password-protected files.

    Args:
        pdf_path: Path to the PDF file
        password: Optional password. If None, extracts from filename.

    Returns:
        pdfplumber.PDF object (context manager)

    Raises:
        Exception: If PDF cannot be opened
    """
    if password is None:
        password = get_password_from_filename(pdf_path)

    # Try opening without password first
    try:
        pdf = pdfplumber.open(pdf_path)
        _ = len(pdf.pages)  # Verify we can read pages
        return pdf
    except Exception:
        pass

    # Try with password
    if password:
        try:
            pdf = pdfplumber.open(pdf_path, password=password)
            print(f"  Opened with password from filename")
            return pdf
        except Exception as e:
            raise Exception(f"Failed to open PDF (tried password '{password}'): {e}")

    raise Exception("Failed to open PDF - may be encrypted")


def convert_date(date_str: str, input_format: str) -> str:
    """Convert date string to standard DD/MM/YYYY format.

    Args:
        date_str: Input date string
        input_format: strptime format string (e.g., '%d %b %y', '%d-%m-%Y')

    Returns:
        Date in DD/MM/YYYY format, or original string if parsing fails
    """
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime('%d/%m/%Y')
    except ValueError:
        # Handle simple replacements
        if '-' in date_str and input_format == '%d-%m-%Y':
            return date_str.replace('-', '/')
        return date_str


def categorize_transaction(description: str) -> str:
    """Categorize transaction based on description.

    Args:
        description: Transaction description

    Returns:
        Category string
    """
    desc_lower = description.lower()

    # EMI categories
    if 'emi' in desc_lower:
        if 'prin' in desc_lower or 'emiprin' in desc_lower:
            return 'EMI Principal'
        elif 'int' in desc_lower or 'emiint' in desc_lower:
            return 'EMI Interest'
        elif 'fee' in desc_lower or 'emifee' in desc_lower:
            return 'EMI Fee'
        elif 'conv' in desc_lower or 'emiconv' in desc_lower:
            return 'EMI Conversion'
        return 'EMI'

    # Tax
    if any(x in desc_lower for x in ['gst', 'igst', 'sgst', 'cgst']):
        return 'Tax'

    # Fees
    if any(x in desc_lower for x in ['annual fee', 'membership fee']):
        return 'Annual Fee'
    if 'replacement fee' in desc_lower:
        return 'Fee'
    if 'waiver' in desc_lower:
        return 'Waiver'

    # Subscriptions
    if any(x in desc_lower for x in ['youtube', 'google', 'netflix', 'spotify', 'prime', 'hotstar']):
        return 'Subscription'

    # Travel
    if any(x in desc_lower for x in ['railway', 'yatra', 'makemytrip']):
        return 'Travel'

    # Food
    if any(x in desc_lower for x in ['swiggy', 'zomato', 'uber eats']):
        return 'Food Delivery'

    # Shopping
    if any(x in desc_lower for x in ['amazon', 'flipkart', 'myntra']):
        return 'Shopping'

    # Fuel
    if any(x in desc_lower for x in ['fuel', 'petrol']):
        return 'Fuel'

    # Payment/Transfer methods
    if any(x in desc_lower for x in ['payment', 'sstu', 'bppy']):
        return 'Payment'
    if 'upi' in desc_lower:
        return 'UPI'
    if 'neft' in desc_lower:
        return 'NEFT Transfer'
    if 'imps' in desc_lower:
        return 'IMPS'
    if 'atm' in desc_lower:
        return 'ATM'

    # Interest/Dividend
    if any(x in desc_lower for x in ['int.pd', 'interest']):
        return 'Interest'
    if 'dividend' in desc_lower:
        return 'Dividend'
    if 'achcr' in desc_lower:
        return 'Dividend/Credit'

    return 'Purchase'


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize DataFrame columns to standard schema.

    Standard schema:
    - Date: str (DD/MM/YYYY format)
    - Description: str
    - Amount: float (positive)
    - Type: str ("Debit" or "Credit")
    - Category: str

    Args:
        df: Input DataFrame with various column names

    Returns:
        DataFrame with standardized columns
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Type', 'Category'])

    df = df.copy()

    # Rename common column variations
    rename_map = {
        'Transaction Details': 'Description',
        'Narration': 'Description',
        'Particulars': 'Description',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Ensure standard columns exist
    standard_cols = ['Date', 'Description', 'Amount', 'Type', 'Category']
    for col in standard_cols:
        if col not in df.columns:
            df[col] = ''

    # Clean Amount column - ensure it's numeric
    if 'Amount' in df.columns:
        df['Amount'] = df['Amount'].astype(str).str.replace(',', '', regex=False)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # Select only standard columns
    return df[standard_cols]


def save_results(df: pd.DataFrame, pdf_path: str, output_dir: str = "output") -> str:
    """Save extracted transactions to CSV, Excel, and JSON summary.

    Args:
        df: DataFrame with transactions
        pdf_path: Source PDF path (used for naming output folder)
        output_dir: Base output directory

    Returns:
        Path to output folder
    """
    if df is None or df.empty:
        return ""

    df = df.copy()
    pdf_name = Path(pdf_path).stem
    output_folder = os.path.join(output_dir, pdf_name)
    os.makedirs(output_folder, exist_ok=True)

    # Sort by date if possible
    try:
        df['_date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values('_date')
        df = df.drop('_date', axis=1)
    except Exception:
        pass

    # Save CSV
    csv_path = os.path.join(output_folder, "transactions.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved to {csv_path}")

    # Save Excel
    excel_path = os.path.join(output_folder, "transactions.xlsx")
    df.to_excel(excel_path, index=False)
    print(f"Saved to {excel_path}")

    # Calculate summary statistics
    total = len(df)
    debits = len(df[df['Type'] == 'Debit']) if 'Type' in df.columns else 0
    credits = len(df[df['Type'] == 'Credit']) if 'Type' in df.columns else 0

    # Print summary
    print(f"\nSummary:")
    print(f"  Total transactions: {total}")
    print(f"  Debits: {debits}")
    print(f"  Credits: {credits}")

    # Save summary JSON
    summary = {
        "extraction_timestamp": datetime.now().isoformat(),
        "source_pdf": pdf_path,
        "total_transactions": total,
        "debits": debits,
        "credits": credits,
        "columns": list(df.columns)
    }
    summary_path = os.path.join(output_folder, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {summary_path}")

    return output_folder
