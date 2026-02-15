"""
HDFC Credit Card Statement Extraction
"""

import re
from pathlib import Path
from typing import List
import pandas as pd

from .base import CreditCardExtractor


class HDFCCCExtractor(CreditCardExtractor):
    """Extract transactions from HDFC credit card statements."""

    # File patterns this extractor handles
    FILE_PATTERNS = ["5241*"]
    BANK_NAME = "HDFC CC"

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
                    if not table or not table[0]:
                        continue
                    # Find transaction table by header
                    if 'DATE' in str(table[0]) and 'TRANSACTION' in str(table[0]):
                        page_txns = self._parse_table(table[1:])  # Skip header
                        if page_txns:
                            print(f"  Page {page_num}: {len(page_txns)} transactions")
                            self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount', 'Type'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        return df

    def _parse_table(self, rows: list) -> List[dict]:
        """Parse transactions from table rows."""
        transactions = []

        date_pattern = r'(\d{2}/\d{2}/\d{4})\|'
        amount_pattern = r'(\+)?\s*C\s*([\d,]+\.?\d*)\s*l'

        for row in rows:
            if not row or not row[0]:
                continue

            cell_text = row[0]
            if not cell_text:
                continue

            date_match = re.search(date_pattern, cell_text)
            if not date_match:
                continue

            date_str = date_match.group(1)

            amount_match = re.search(amount_pattern, cell_text)
            if not amount_match:
                continue

            is_credit = amount_match.group(1) == '+'
            amount = amount_match.group(2).replace(',', '')

            lines = cell_text.split('\n')
            description = lines[0].strip()

            if description.isupper() and len(description.split()) <= 3:
                if len(lines) > 1:
                    description = lines[1].split('(Ref#')[0].strip()
            else:
                description = description.split('(Ref#')[0].strip()

            if 'DATE' in description or 'TRANSACTION' in description:
                continue

            txn_type = 'Credit' if is_credit else 'Debit'
            category = self.categorize_transaction(description)

            try:
                amount_float = float(amount)
            except ValueError:
                amount_float = 0.0

            transactions.append({
                'Date': date_str,
                'Description': description,
                'Amount': amount_float,
                'Type': txn_type,
                'Category': category
            })

        return transactions


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("5241*.pdf"))

    if not pdf_files:
        print("No HDFC credit card PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = HDFCCCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
