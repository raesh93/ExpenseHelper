"""
SBI Credit Card Statement Extraction
"""

import re
from pathlib import Path
from datetime import datetime
from typing import List
import pandas as pd

from .base import CreditCardExtractor


class SBICCExtractor(CreditCardExtractor):
    """Extract transactions from SBI credit card statements."""

    FILE_PATTERNS = ["0992*"]
    BANK_NAME = "SBI CC"

    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.transactions: List[dict] = []

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self.open_pdf() as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = str(table[0])
                    if 'Date' in header and 'Transaction' in header and 'Amount' in header:
                        page_txns = self._parse_table(table)
                        if page_txns:
                            print(f"  Page {page_num}: {len(page_txns)} transactions")
                            self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        print(f"\nTotal transactions: {len(df)}")

        return df

    def _parse_table(self, table: list) -> List[dict]:
        """Parse transactions from SBI table format."""
        transactions = []

        for row in table[1:]:
            if not row or len(row) < 3:
                continue

            dates_str = row[0] or ""
            descs_str = row[1] or ""
            amounts_str = row[2] or ""

            dates = [d.strip() for d in dates_str.split('\n') if d.strip()]
            descs = [d.strip() for d in descs_str.split('\n') if d.strip()]
            amounts = [a.strip() for a in amounts_str.split('\n') if a.strip()]

            filtered_descs = [d for d in descs if not d.startswith('TRANSACTIONS FOR')]

            date_idx = 0
            current_date = dates[0] if dates else ""

            for i, desc in enumerate(filtered_descs):
                if i < len(amounts):
                    amount_str = amounts[i]

                    if date_idx < len(dates):
                        current_date = dates[date_idx]
                        if date_idx + 1 < len(dates) and i + 1 < len(filtered_descs):
                            date_idx += 1

                    amount_match = re.match(r'([\d,]+\.?\d*)\s*([DC])', amount_str)
                    if not amount_match:
                        continue

                    amount = amount_match.group(1).replace(',', '')
                    txn_type = 'Credit' if amount_match.group(2) == 'C' else 'Debit'

                    date_formatted = self._convert_date(current_date)
                    category = self.categorize_transaction(desc)

                    try:
                        amount_float = float(amount)
                    except ValueError:
                        amount_float = 0.0

                    transactions.append({
                        'Date': date_formatted,
                        'Description': desc,
                        'Amount': amount_float,
                        'Type': txn_type,
                        'Category': category
                    })

        return transactions

    def _convert_date(self, date_str: str) -> str:
        """Convert 'DD MMM YY' to 'DD/MM/YYYY'."""
        try:
            dt = datetime.strptime(date_str, '%d %b %y')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            return date_str


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("0992*.pdf"))

    if not pdf_files:
        print("No SBI credit card PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = SBICCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
