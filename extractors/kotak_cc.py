"""
Kotak Credit Card Statement Extraction
"""

import re
from pathlib import Path
from typing import List
import pandas as pd

from .base import CreditCardExtractor


class KotakCCExtractor(CreditCardExtractor):
    """Extract transactions from Kotak credit card statements."""

    FILE_PATTERNS = ["00114*", "00116*"]
    BANK_NAME = "Kotak CC"

    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.transactions: List[dict] = []

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self.open_pdf() as pdf:
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
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount', 'Type'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        return df

    def _parse_transactions(self, text: str) -> List[dict]:
        """Parse transactions from raw text."""
        transactions = []
        lines = text.split('\n')

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
            amount = match.group(3).replace(',', '')
            is_credit = match.group(4) is not None

            if 'TotalPurchase' in description or 'TotalAmount' in description:
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
    pdf_files = list(pdf_dir.glob("00114452*.pdf"))

    if not pdf_files:
        print("No Kotak credit card PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = KotakCCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
