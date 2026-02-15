"""
Base extractor class with shared functionality.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod
import pdfplumber
import pandas as pd


class BaseExtractor(ABC):
    """Base class for all statement extractors."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    @staticmethod
    def get_password_from_filename(filepath: str) -> str:
        """Extract password from filename (last segment after '_')."""
        filename = Path(filepath).stem
        parts = filename.split('_')
        return parts[-1] if parts else ""

    def open_pdf(self, password: Optional[str] = None):
        """Open PDF, handling password-protected files.

        Returns:
            pdfplumber.PDF object (context manager)
        """
        if password is None:
            password = self.get_password_from_filename(self.pdf_path)

        # Try opening without password first
        try:
            pdf = pdfplumber.open(self.pdf_path)
            _ = len(pdf.pages)  # Verify we can read pages
            return pdf
        except Exception:
            pass

        # Try with password
        if password:
            try:
                pdf = pdfplumber.open(self.pdf_path, password=password)
                print(f"  Opened with password from filename")
                return pdf
            except Exception as e:
                raise Exception(f"Failed to open PDF (tried password '{password}'): {e}")

        raise Exception("Failed to open PDF - may be encrypted")

    @abstractmethod
    def extract_transactions(self) -> pd.DataFrame:
        """Extract transactions from the PDF. Must be implemented by subclasses."""
        pass

    def save_results(self, df: pd.DataFrame, output_dir: str = "output") -> str:
        """Save extracted transactions to CSV, Excel, and JSON summary."""
        if df is None or df.empty:
            return ""

        df = df.copy()
        pdf_name = Path(self.pdf_path).stem
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
            "source_pdf": self.pdf_path,
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


class CreditCardExtractor(BaseExtractor):
    """Base class for credit card extractors. Includes categorization."""

    def categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description."""
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

        return 'Purchase'


class DebitAccountExtractor(BaseExtractor):
    """Base class for debit/savings account extractors. No categorization."""
    pass
