"""
Kotak Bank Statement Extraction
Extracts transactions from Kotak Bank PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List, Optional


class KotakExtractor:
    """Extract transactions from Kotak Bank statements."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.transactions: List[dict] = []

    def _get_password_from_filename(self) -> str:
        """Extract password from filename (last segment when split by '_')."""
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
        # Remove duplicates based on Date + Description + Amount (more reliable than Reference)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        # Filter to savings account only (exclude term deposit transactions)
        df = self.filter_savings_account(df)
        print(f"Filtered to savings account: {len(df)} transactions")

        return df

    def _parse_transactions(self, text: str) -> List[dict]:
        """Parse transactions from raw text."""
        transactions = []
        lines = text.split('\n')

        # Pattern for Kotak transactions:
        # DD Mon, YYYY Description Reference DEBIT/CREDIT BALANCE
        # Example: 01 Dec, 2025 UPI/ICCL - Mutual F/... UPI-533562653043 -5,000.00 44,101.52

        date_pattern = r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4})'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            # Skip header line
            if 'TRANSACTION DETAILS' in rest or 'CHEQUE/REFERENCE' in rest:
                continue

            # Skip opening/closing balance lines
            if 'OPENING BALANCE' in rest or 'Opening Balance' in rest:
                continue
            if 'CLOSING BALANCE' in rest or 'Closing Balance' in rest:
                continue

            # Skip date range lines like "01 Dec, 2025 - 31 Dec, 2025"
            # These start with " - DD Mon, YYYY" after removing first date
            if re.match(r'^\s*-\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4}\s*$', rest):
                continue

            # Parse the rest: Description Reference Amount Balance
            txn = self._parse_transaction_line(date_str, rest)
            if txn:
                transactions.append(txn)

        return transactions

    def _parse_transaction_line(self, date_str: str, rest: str) -> Optional[dict]:
        """Parse a single transaction line."""
        # Find amounts at the end (negative for debit, positive for credit)
        # Pattern: -1,234.56 or +1,234.56 or 1,234.56
        amount_pattern = r'([+-]?[\d,]+\.\d{2})\s*$'

        # Find balance (last amount)
        balance_match = re.search(amount_pattern, rest)
        if not balance_match:
            return None

        balance = balance_match.group(1)
        rest = rest[:balance_match.start()].strip()

        # Find debit/credit amount (second to last amount)
        amount_match = re.search(amount_pattern, rest)
        if not amount_match:
            return None

        amount = amount_match.group(1)
        rest = rest[:amount_match.start()].strip()

        # Check if there's another amount (credit column when debit is empty or vice versa)
        # Some lines have: Description Reference -5000.00 (blank) 44101.52
        # Others have: Description Reference (blank) +6076.02 45177.54
        another_amount = re.search(amount_pattern, rest)
        if another_amount:
            # There was a third amount, so amount was actually balance
            # and this is the real amount
            balance = amount
            amount = another_amount.group(1)
            rest = rest[:another_amount.start()].strip()

        # Now rest contains: Description Reference
        # Reference patterns: UPI-XXXX, NACHDB..., NEFTINW-..., account numbers, etc.
        ref_pattern = r'(UPI-\d+|NACH\w+|NEFT\w+-\d+|\[\d+\]|\d{10,}TO|\d{10,})$'
        ref_match = re.search(ref_pattern, rest)

        if ref_match:
            reference = ref_match.group(1)
            description = rest[:ref_match.start()].strip()
        else:
            # No standard reference found - use description as-is
            description = rest
            reference = ""

        # Clean up amount (remove + sign, keep - for debits)
        if amount.startswith('+'):
            amount = amount[1:]
            txn_type = 'Credit'
        elif amount.startswith('-'):
            amount = amount[1:]
            txn_type = 'Debit'
        else:
            # Determine from balance change
            txn_type = 'Unknown'

        return {
            'Date': date_str,
            'Description': description.strip(),
            'Reference': reference.strip(),
            'Amount': amount,
            'Type': txn_type,
            'Balance': balance.replace('+', '').replace('-', '')
        }

    def filter_savings_account(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to only savings account transactions (exclude term deposit accounts)."""
        # Term deposit patterns (pages 10-12)
        term_patterns = ['Tran. For Principal', 'Sweep Trf To:', 'Closure Int After Tax',
                         'SWEEP TRANSFER FROM', 'Opening Balance', 'Closing Balance']

        def is_term_deposit(desc):
            return any(p in desc for p in term_patterns)

        savings_df = df[~df['Description'].apply(is_term_deposit)]
        return savings_df

    def save_results(self, df: pd.DataFrame, output_dir: str = "output"):
        """Save the extracted transactions."""
        if df.empty:
            return

        df = df.copy()

        pdf_name = Path(self.pdf_path).stem
        output_folder = os.path.join(output_dir, pdf_name)
        os.makedirs(output_folder, exist_ok=True)

        # Sort by date
        try:
            df['_date'] = pd.to_datetime(df['Date'], format='%d %b, %Y')
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

        # Save summary
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_transactions": len(df),
            "columns": list(df.columns)
        }
        summary_path = os.path.join(output_folder, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {summary_path}")


def main():
    """Main execution."""
    # Look for Kotak PDFs - they typically have specific naming
    pdf_dir = Path("encrypted_pdf")

    # Find PDFs that look like Kotak statements
    pdf_files = list(pdf_dir.glob("6006279*.pdf"))

    if not pdf_files:
        print("No Kotak PDF files found in 'encrypted_pdf' folder.")
        print("Looking for files matching: 6006279*.pdf")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = KotakExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
