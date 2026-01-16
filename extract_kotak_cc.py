"""
Kotak Credit Card Statement Extraction
Extracts transactions from Kotak credit card PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List, Optional


class KotakCCExtractor:
    """Extract transactions from Kotak credit card statements."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.transactions: List[dict] = []

    def _get_password_from_filename(self) -> str:
        """Extract password from filename (last segment after '_')."""
        filename = Path(self.pdf_path).stem
        parts = filename.split('_')
        return parts[-1] if parts else ""

    def _open_pdf(self):
        """Open PDF, handling password-protected files."""
        password = self._get_password_from_filename()

        # Try opening without password first
        try:
            pdf = pdfplumber.open(self.pdf_path)
            _ = len(pdf.pages)
            return pdf
        except Exception:
            pass

        # Try with password extracted from filename
        if password:
            try:
                pdf = pdfplumber.open(self.pdf_path, password=password)
                print(f"  Opened with password from filename")
                return pdf
            except Exception as e:
                raise Exception(f"Failed to open PDF (tried password '{password}'): {e}")

        raise Exception("Failed to open PDF - may be encrypted")

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self._open_pdf() as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                page_txns = self._parse_transactions(text)
                if page_txns:
                    print(f"  Page {page_num}: {len(page_txns)} transactions")
                    self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        # Include Type in deduplication - same amount can be both debit and credit (refund)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount', 'Type'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        return df

    def _parse_transactions(self, text: str) -> List[dict]:
        """Parse transactions from raw text."""
        transactions = []
        lines = text.split('\n')

        # Pattern: DD/MM/YYYY Description Amount [Cr]
        date_pattern = r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})(\s+Cr)?$'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(date_pattern, line)
            if not match:
                continue

            date_str = match.group(1)
            description = match.group(2).strip()
            amount = match.group(3)
            is_credit = match.group(4) is not None

            # Skip summary lines
            if 'TotalPurchase' in description or 'TotalAmount' in description:
                continue

            # Determine transaction type
            txn_type = 'Credit' if is_credit else 'Debit'

            # Categorize transaction
            category = self._categorize(description)

            transactions.append({
                'Date': date_str,
                'Description': description,
                'Amount': amount,
                'Type': txn_type,
                'Category': category
            })

        return transactions

    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description."""
        desc_lower = description.lower()

        if 'emi' in desc_lower:
            if 'emiprin' in desc_lower:
                return 'EMI Principal'
            elif 'emiint' in desc_lower:
                return 'EMI Interest'
            elif 'emifee' in desc_lower:
                return 'EMI Fee'
            elif 'emiconv' in desc_lower:
                return 'EMI Conversion'
            return 'EMI'
        elif 'gst' in desc_lower:
            return 'Tax'
        elif 'youtube' in desc_lower or 'google' in desc_lower or 'netflix' in desc_lower:
            return 'Subscription'
        elif 'railway' in desc_lower or 'yatra' in desc_lower or 'makemytrip' in desc_lower:
            return 'Travel'
        elif 'waiver' in desc_lower:
            return 'Waiver'
        elif any(x in desc_lower for x in ['payment', 'sstu', 'imps', 'neft', 'upi']):
            return 'Payment'

        return 'Purchase'

    def save_results(self, df: pd.DataFrame, output_dir: str = "output"):
        """Save the extracted transactions."""
        if df.empty:
            return

        pdf_name = Path(self.pdf_path).stem
        output_folder = os.path.join(output_dir, pdf_name)
        os.makedirs(output_folder, exist_ok=True)

        # Sort by date
        try:
            df = df.copy()
            df['_date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
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

        # Print summary
        print(f"\nSummary:")
        print(f"  Total transactions: {len(df)}")
        print(f"  Debits: {len(df[df['Type'] == 'Debit'])}")
        print(f"  Credits: {len(df[df['Type'] == 'Credit'])}")

        # Save summary JSON
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_transactions": len(df),
            "debits": len(df[df['Type'] == 'Debit']),
            "credits": len(df[df['Type'] == 'Credit']),
            "columns": list(df.columns)
        }
        summary_path = os.path.join(output_folder, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {summary_path}")


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")

    # Find Kotak credit card PDFs (they have different naming pattern)
    # Pattern: 00114452-XXXXXXXXX..._password.pdf
    pdf_files = list(pdf_dir.glob("00114452*.pdf"))

    if not pdf_files:
        print("No Kotak credit card PDF files found in 'encrypted_pdf' folder.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = KotakCCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
